#!/usr/bin/env python3
"""
monitor_dashboard.py — Dashboard de series de tiempo del monitor de MITgcm.

Lee los campos %MON del STDOUT.0000 de cada run dir, los acumula en un CSV
(historial continuo a traves de las 2 etapas, ya que time_tsnumber es monotono:
0->7200 etapa1, 7200->14400 etapa2) y genera un PNG multi-panel con la
evolucion: energia cinetica, rango de eta, |u|/|v| max, CFL advectivo y theta.

Uso:
  ml load herramientas/python/3.11.8
  python3 monitor_dashboard.py            # usa run_expand y run_expand_nobay
  python3 monitor_dashboard.py <dir> ...  # run dirs especificos

Salida:
  monitor_dashboard.png        (figura)
  monitor_<caso>.csv           (historial acumulado por caso)
Para reiniciar el historial: borra los monitor_<caso>.csv.
"""
import os, re, sys, csv, time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

EXP = os.path.dirname(os.path.abspath(__file__))
MON_RE = re.compile(r"%MON\s+(\S+)\s*=\s*([-+0-9.][-+0-9.eEdD]*)")

KEYS = ["time_tsnumber", "time_secondsf",
        "ke_mean", "ke_max",
        "dynstat_eta_max", "dynstat_eta_min", "dynstat_eta_mean",
        "dynstat_uvel_max", "dynstat_uvel_min",
        "dynstat_vvel_max", "dynstat_vvel_min",
        "advcfl_uvel_max", "advcfl_vvel_max", "advcfl_wvel_max",
        "dynstat_theta_max", "dynstat_theta_min"]


def parse_stdout(path):
    """Devuelve dict {key: np.array} alineado por bloque de monitor dinamico."""
    recs, cur = [], None
    with open(path, "r", errors="ignore") as f:
        for line in f:
            m = MON_RE.search(line)
            if not m:
                continue
            k, v = m.group(1), m.group(2).replace("D", "E").replace("d", "e")
            if k == "time_tsnumber":          # inicia bloque dinamico nuevo
                if cur:
                    recs.append(cur)
                cur = {}
            if cur is None:                   # bloque de grilla inicial -> ignorar
                continue
            try:
                cur[k] = float(v)
            except ValueError:
                pass
        if cur:
            recs.append(cur)
    if not recs:
        return None
    return {k: np.array([r.get(k, np.nan) for r in recs]) for k in KEYS}


def csv_path(name):
    return os.path.join(EXP, f"monitor_{name}.csv")


def _arrs_from_rows(rows):
    ks = sorted(rows)
    return {k: np.array([rows[ts][k] for ts in ks]) for k in KEYS}


def load_csv(name):
    path = csv_path(name)
    rows = {}
    if os.path.isfile(path):
        with open(path, newline="") as f:
            for d in csv.DictReader(f):
                try:
                    ts = int(float(d["time_tsnumber"]))
                except (KeyError, ValueError):
                    continue
                rows[ts] = {k: (float(d[k]) if d.get(k, "") not in ("", "nan")
                                else np.nan) for k in KEYS}
    return rows


def merge_csv(name, parsed):
    """Mezcla los registros parseados al CSV (clave = time_tsnumber) y reescribe."""
    rows = load_csv(name)
    n = len(parsed["time_tsnumber"])
    for i in range(n):
        ts = parsed["time_tsnumber"][i]
        if not np.isfinite(ts):
            continue
        rows[int(ts)] = {k: parsed[k][i] for k in KEYS}
    with open(csv_path(name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=KEYS)
        w.writeheader()
        for ts in sorted(rows):
            w.writerow({k: rows[ts][k] for k in KEYS})
    return _arrs_from_rows(rows)


def which_stage(d):
    if os.path.isfile(os.path.join(d, "output_stage2.txt")):
        return "stage2"
    if os.path.isfile(os.path.join(d, "output_stage1.txt")):
        return "stage1"
    return "?"


def load_all(dirs):
    data = {}
    for d in dirs:
        name = os.path.basename(d)
        f = os.path.join(d, "STDOUT.0000")
        parsed = parse_stdout(f) if os.path.isfile(f) else None
        if parsed is not None and len(parsed["time_tsnumber"]):
            data[name] = merge_csv(name, parsed)        # acumula + devuelve historial
        elif os.path.isfile(csv_path(name)):
            data[name] = _arrs_from_rows(load_csv(name))  # solo historial guardado
    return data


def main():
    dirs = sys.argv[1:] or [os.path.join(EXP, "run_expand"),
                            os.path.join(EXP, "run_expand_nobay")]
    data = load_all(dirs)

    fig, axes = plt.subplots(3, 2, figsize=(13, 11))
    colors = {"run_expand": "tab:blue", "run_expand_nobay": "tab:orange"}

    def x(of):
        t = of["time_secondsf"]
        return (t / 3600.0, "tiempo [h]") if np.isfinite(t).any() else \
               (of["time_tsnumber"], "paso de tiempo")

    xlabel = "tiempo [h]"
    if not data:
        for ax in axes.ravel():
            ax.text(0.5, 0.5, "sin datos de monitor todavia\n(esperando STDOUT.0000)",
                    ha="center", va="center")
        msg = "sin datos"
    else:
        for name, of in data.items():
            c = colors.get(name, "tab:green")
            xv, xlabel = x(of)
            # 1) energia cinetica (mean solido + max punteado, ambos con label)
            axes[0, 0].plot(xv, of["ke_mean"], color=c, label=f"{name} mean")
            axes[0, 0].plot(xv, of["ke_max"], color=c, ls="--", alpha=0.6, label=f"{name} max")
            # 2) elevacion eta (rango)
            axes[0, 1].plot(xv, of["dynstat_eta_max"], color=c, label=name)
            axes[0, 1].plot(xv, of["dynstat_eta_min"], color=c)
            axes[0, 1].fill_between(xv, of["dynstat_eta_min"], of["dynstat_eta_max"],
                                    color=c, alpha=0.15)
            # 3) velocidades max
            axes[1, 0].plot(xv, np.abs(of["dynstat_uvel_max"]), color=c, label=f"{name} |u|max")
            axes[1, 0].plot(xv, np.abs(of["dynstat_vvel_max"]), color=c, ls="--", label=f"{name} |v|max")
            # 4) CFL advectivo
            axes[1, 1].plot(xv, of["advcfl_uvel_max"], color=c, label=f"{name} CFL_u")
            axes[1, 1].plot(xv, of["advcfl_vvel_max"], color=c, ls="--", label=f"{name} CFL_v")
            axes[1, 1].plot(xv, of["advcfl_wvel_max"], color=c, ls=":", label=f"{name} CFL_w")
            # 5) theta (chequeo barotropico)
            axes[2, 0].plot(xv, of["dynstat_theta_max"], color=c, label=f"{name} max")
            axes[2, 0].plot(xv, of["dynstat_theta_min"], color=c, ls="--", label=f"{name} min")
        msg = ", ".join(f"{n}:{len(d['time_tsnumber'])} pts" for n, d in data.items())

        axes[0, 0].set(title="Energia cinetica", ylabel="KE [m2/s2]", xlabel=xlabel)
        axes[0, 1].set(title="Elevacion superficie eta (rango max-min)", ylabel="eta [m]", xlabel=xlabel)
        axes[1, 0].set(title="Velocidad horizontal max  |u| (solido), |v| (punteado)", ylabel="m/s", xlabel=xlabel)
        axes[1, 1].set(title="CFL advectivo (u solido, v punteado, w :) — debe ser < 1", ylabel="CFL", xlabel=xlabel)
        axes[1, 1].axhline(1.0, color="red", lw=1, alpha=0.6)
        axes[2, 0].set(title="Temperatura theta — BAROTROPICO: debe ser plano 33.6", ylabel="theta [C]", xlabel=xlabel)
        for ax in [axes[0,0],axes[0,1],axes[1,0],axes[1,1],axes[2,0]]:
            ax.grid(alpha=0.3); ax.legend(fontsize=7, loc="best")

    # panel de estado (texto)
    axes[2, 1].axis("off")
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"Actualizado: {stamp}", ""]
    for name, of in (data or {}).items():
        n = of["time_tsnumber"]
        last = int(n[-1]) if len(n) and np.isfinite(n[-1]) else "?"
        tmin = of["dynstat_theta_min"][-1] if len(of["dynstat_theta_min"]) else np.nan
        tmax = of["dynstat_theta_max"][-1] if len(of["dynstat_theta_max"]) else np.nan
        cfl = np.nanmax(of["advcfl_uvel_max"]) if len(of["advcfl_uvel_max"]) else np.nan
        lines += [f"{name} ({which_stage(os.path.join(EXP,name))})",
                  f"   paso actual : {last} / 14400 (2 etapas)",
                  f"   theta min/max: {tmin:.3f} / {tmax:.3f}",
                  f"   CFL_u max   : {cfl:.3f}", ""]
    axes[2, 1].text(0.02, 0.98, "\n".join(lines), va="top", ha="left",
                    family="monospace", fontsize=10)

    fig.suptitle("MITgcm — Bahia barotropica: monitor de simulaciones", fontsize=14, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    out = os.path.join(EXP, "monitor_dashboard.png")
    fig.savefig(out, dpi=110)
    print(f"[{stamp}] dashboard -> {out}  ({msg})")


if __name__ == "__main__":
    main()
