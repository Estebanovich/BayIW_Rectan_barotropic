#!/usr/bin/env python3
"""
monitor_dashboard.py — Dashboard de series de tiempo del monitor de MITgcm.

Lee los campos %MON del STDOUT.0000 de cada run dir (etapa en curso) y genera
un PNG multi-panel con la salud/evolucion de la corrida:
  energia cinetica, rango de eta, |u|/|v| max, CFL advectivo y theta.

Uso:
  ml load herramientas/python/3.11.8
  python3 monitor_dashboard.py            # usa run_expand y run_expand_nobay
  python3 monitor_dashboard.py <dir> ...  # run dirs especificos

Salida: monitor_dashboard.png (en este directorio)
Refresco: lo regenera el /loop cada 15 min, o corre este script cuando quieras.
"""
import os, re, sys, glob, time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

EXP = os.path.dirname(os.path.abspath(__file__))
MON_RE = re.compile(r"%MON\s+(\S+)\s*=\s*([-+0-9.][-+0-9.eEdD]*)")

# campos que nos interesan (clave -> usado en paneles)
KEYS = ["time_tsnumber", "time_secondsf",
        "ke_mean", "ke_max",
        "dynstat_eta_max", "dynstat_eta_min", "dynstat_eta_mean",
        "dynstat_uvel_max", "dynstat_uvel_min",
        "dynstat_vvel_max", "dynstat_vvel_min",
        "advcfl_uvel_max", "advcfl_vvel_max", "advcfl_wvel_max",
        "dynstat_theta_max", "dynstat_theta_min"]


def parse_stdout(path):
    """Devuelve dict {key: np.array} alineado por bloque de monitor dinamico."""
    recs = []
    cur = None
    with open(path, "r", errors="ignore") as f:
        for line in f:
            m = MON_RE.search(line)
            if not m:
                continue
            k, v = m.group(1), m.group(2).replace("D", "E").replace("d", "e")
            if k == "time_tsnumber":          # inicia un bloque dinamico nuevo
                if cur:
                    recs.append(cur)
                cur = {}
            if cur is None:                   # aun en el bloque de grilla inicial
                continue
            try:
                cur[k] = float(v)
            except ValueError:
                pass
        if cur:
            recs.append(cur)
    if not recs:
        return None
    out = {k: np.array([r.get(k, np.nan) for r in recs]) for k in KEYS}
    return out


def load_all(dirs):
    data = {}
    for d in dirs:
        f = os.path.join(d, "STDOUT.0000")
        if os.path.isfile(f):
            parsed = parse_stdout(f)
            if parsed is not None and len(parsed["time_tsnumber"]) > 0:
                data[os.path.basename(d)] = parsed
    return data


def which_stage(d):
    s1 = os.path.join(d, "output_stage1.txt")
    s2 = os.path.join(d, "output_stage2.txt")
    if os.path.isfile(s2):
        return "stage2"
    if os.path.isfile(s1):
        return "stage1"
    return "?"


def main():
    dirs = sys.argv[1:] or [os.path.join(EXP, "run_expand"),
                            os.path.join(EXP, "run_expand_nobay")]
    data = load_all(dirs)

    fig, axes = plt.subplots(3, 2, figsize=(13, 11))
    colors = {"run_expand": "tab:blue", "run_expand_nobay": "tab:orange"}

    def x(of):  # eje temporal en horas si hay time_secondsf, si no en pasos
        t = of["time_secondsf"]
        return (t / 3600.0, "tiempo [h]") if np.isfinite(t).any() else \
               (of["time_tsnumber"], "paso de tiempo")

    if not data:
        for ax in axes.ravel():
            ax.text(0.5, 0.5, "sin datos de monitor todavia\n(esperando STDOUT.0000)",
                    ha="center", va="center")
        msg = "sin datos"
    else:
        for name, of in data.items():
            c = colors.get(name, "tab:green")
            xv, xl = x(of)
            st = which_stage(os.path.join(EXP, name))
            lab = f"{name} ({st})"
            # 1) energia cinetica
            axes[0, 0].plot(xv, of["ke_mean"], color=c, label=lab)
            axes[0, 0].plot(xv, of["ke_max"], color=c, ls="--", alpha=0.5)
            # 2) elevacion eta (rango)
            axes[0, 1].plot(xv, of["dynstat_eta_max"], color=c, label=lab)
            axes[0, 1].plot(xv, of["dynstat_eta_min"], color=c)
            axes[0, 1].fill_between(xv, of["dynstat_eta_min"], of["dynstat_eta_max"],
                                    color=c, alpha=0.15)
            # 3) velocidades max
            axes[1, 0].plot(xv, np.abs(of["dynstat_uvel_max"]), color=c, label=f"{name} |u|max")
            axes[1, 0].plot(xv, np.abs(of["dynstat_vvel_max"]), color=c, ls="--", label=f"{name} |v|max")
            # 4) CFL advectivo
            axes[1, 1].plot(xv, of["advcfl_uvel_max"], color=c, label=f"{name} CFL_u")
            axes[1, 1].plot(xv, of["advcfl_vvel_max"], color=c, ls="--")
            axes[1, 1].plot(xv, of["advcfl_wvel_max"], color=c, ls=":")
            # 5) theta (chequeo barotropico)
            axes[2, 0].plot(xv, of["dynstat_theta_max"], color=c, label=f"{name} max")
            axes[2, 0].plot(xv, of["dynstat_theta_min"], color=c, ls="--", label=f"{name} min")
            xlabel = xl
        msg = ", ".join(f"{n}:{len(d['time_tsnumber'])} pts" for n, d in data.items())

        axes[0, 0].set(title="Energia cinetica (mean solido, max punteado)", ylabel="KE [m2/s2]", xlabel=xlabel)
        axes[0, 1].set(title="Elevacion superficie eta (rango max-min)", ylabel="eta [m]", xlabel=xlabel)
        axes[1, 0].set(title="Velocidad horizontal max  |u| (solido), |v| (punteado)", ylabel="m/s", xlabel=xlabel)
        axes[1, 1].set(title="CFL advectivo (u solido, v punteado, w :) — debe ser < 1", ylabel="CFL", xlabel=xlabel)
        axes[1, 1].axhline(1.0, color="red", lw=1, ls="-", alpha=0.6)
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
                  f"   paso actual : {last} / 7200",
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
