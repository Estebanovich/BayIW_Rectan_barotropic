#!/usr/bin/env python3
"""
fill_gap_from_nc.py — Reconstruye el monitor (eta/u/v/theta/ke) desde los
volcados NetCDF de una etapa y rellena los huecos del CSV del dashboard.

Util cuando el dashboard, por muestrear cada 15 min, no alcanzo a capturar
parte del STDOUT antes de que la etapa siguiente lo sobreescribiera.

Para max/min/mean NO se pegan los tiles: se agrega sobre los 20.

Uso:
  ml load herramientas/python/3.11.8
  python3 fill_gap_from_nc.py run_expand OUT_stage1
  python3 fill_gap_from_nc.py run_expand OUT_stage2
"""
import os, sys, csv, glob
import numpy as np
import netCDF4 as nc

EXP = os.path.dirname(os.path.abspath(__file__))
DELTAT = 30.0
KEYS = ["time_tsnumber", "time_secondsf",
        "ke_mean", "ke_max",
        "dynstat_eta_max", "dynstat_eta_min", "dynstat_eta_mean",
        "dynstat_uvel_max", "dynstat_uvel_min",
        "dynstat_vvel_max", "dynstat_vvel_min",
        "advcfl_uvel_max", "advcfl_vvel_max", "advcfl_wvel_max",
        "dynstat_theta_max", "dynstat_theta_min"]


def reconstruct(outdir):
    tiles = sorted(glob.glob(os.path.join(outdir, "mnc_*")))
    agg = {}
    for td in tiles:
        for sf in sorted(glob.glob(os.path.join(td, "state.*.nc"))):
            ds = nc.Dataset(sf)
            iters = np.array(ds.variables["iter"][:], dtype=int)
            Eta, U, V, T = (ds.variables[k] for k in ("Eta", "U", "V", "Temp"))
            for ti, it in enumerate(iters):
                e = np.asarray(Eta[ti]); u = np.asarray(U[ti])
                v = np.asarray(V[ti]); tt = np.asarray(T[ti])
                wet = tt > 1.0
                uc = 0.5 * (u[:, :, :-1] + u[:, :, 1:])     # (Z,Y,X)
                vc = 0.5 * (v[:, :-1, :] + v[:, 1:, :])
                ke = 0.5 * (uc ** 2 + vc ** 2)
                a = agg.setdefault(int(it), dict(emax=-1e30, emin=1e30, esum=0.0, ecnt=0,
                                                 umax=-1e30, umin=1e30, vmax=-1e30, vmin=1e30,
                                                 tmax=-1e30, tmin=1e30,
                                                 kesum=0.0, kecnt=0, kemax=-1e30))
                a["emax"] = max(a["emax"], e.max()); a["emin"] = min(a["emin"], e.min())
                a["esum"] += e.sum(); a["ecnt"] += e.size
                a["umax"] = max(a["umax"], u.max()); a["umin"] = min(a["umin"], u.min())
                a["vmax"] = max(a["vmax"], v.max()); a["vmin"] = min(a["vmin"], v.min())
                if wet.any():
                    a["tmax"] = max(a["tmax"], tt[wet].max()); a["tmin"] = min(a["tmin"], tt[wet].min())
                    kw = ke[wet]
                    a["kesum"] += kw.sum(); a["kecnt"] += kw.size
                    a["kemax"] = max(a["kemax"], kw.max())
            ds.close()
    rows = {}
    for it, a in agg.items():
        r = dict.fromkeys(KEYS, np.nan)
        r["time_tsnumber"] = it
        r["time_secondsf"] = it * DELTAT
        r["dynstat_eta_max"] = a["emax"]; r["dynstat_eta_min"] = a["emin"]
        r["dynstat_eta_mean"] = a["esum"] / max(a["ecnt"], 1)
        r["dynstat_uvel_max"] = a["umax"]; r["dynstat_uvel_min"] = a["umin"]
        r["dynstat_vvel_max"] = a["vmax"]; r["dynstat_vvel_min"] = a["vmin"]
        r["dynstat_theta_max"] = a["tmax"]; r["dynstat_theta_min"] = a["tmin"]
        # ke NO se reconstruye: el monitor lo pondera por volumen y una
        # media simple desde snapshots da otra escala -> se deja NaN
        rows[it] = r
    return rows


def merge_into_csv(case, new_rows):
    path = os.path.join(EXP, f"monitor_{case}.csv")
    rows = {}
    if os.path.isfile(path):
        with open(path, newline="") as f:
            for d in csv.DictReader(f):
                try:
                    ts = int(float(d["time_tsnumber"]))
                except (KeyError, ValueError):
                    continue
                rows[ts] = {k: (float(d[k]) if d.get(k, "") not in ("", "nan") else np.nan)
                            for k in KEYS}
    added = 0
    for ts, r in new_rows.items():
        if ts not in rows:              # solo rellenar huecos, no pisar el monitor real
            rows[ts] = r; added += 1
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=KEYS)
        w.writeheader()
        for ts in sorted(rows):
            w.writerow({k: rows[ts][k] for k in KEYS})
    return path, added, rows


def main():
    case = sys.argv[1] if len(sys.argv) > 1 else "run_expand"
    stage = sys.argv[2] if len(sys.argv) > 2 else "OUT_stage1"
    outdir = os.path.join(EXP, case, stage)
    if not os.path.isdir(outdir):
        print(f"no existe {outdir}"); return
    print(f"reconstruyendo {case}/{stage} ...")
    new = reconstruct(outdir)
    print(f"  {len(new)} registros reconstruidos, iters {min(new)}..{max(new)}")
    # validacion contra el CSV existente en iters que se solapen
    path = os.path.join(EXP, f"monitor_{case}.csv")
    existing = {}
    if os.path.isfile(path):
        with open(path, newline="") as f:
            for d in csv.DictReader(f):
                existing[int(float(d["time_tsnumber"]))] = d
    print("  validacion (NetCDF vs monitor) en iters solapados:")
    for it in sorted(new):
        if it in existing:
            e = existing[it]
            print(f"    it={it}: eta_max nc={new[it]['dynstat_eta_max']:+.3e} mon={float(e['dynstat_eta_max']):+.3e} | "
                  f"uvel_max nc={new[it]['dynstat_uvel_max']:.3e} mon={float(e['dynstat_uvel_max']):.3e} | "
                  f"ke_mean nc={new[it]['ke_mean']:.3e} mon={float(e['ke_mean']):.3e}")
    p, added, _ = merge_into_csv(case, new)
    print(f"  rellenados {added} huecos en {os.path.basename(p)}")


if __name__ == "__main__":
    main()
