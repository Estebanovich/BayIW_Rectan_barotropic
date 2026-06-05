#!/usr/bin/env python3
"""
gen_bathy_5km.py — Genera la batimetria REAL de 5 km (560x352) para el caso
de la bahia rectangular, equivalente a bahia_rectan_impar_func.ipynb pero sin
el paso interp2d (que interpola un dominio analitico de ~130 M de puntos y
explota en memoria/tiempo).

Reusa el MISMO build_new_domain del notebook para definir la malla destino
(identica resolucion/origen) y evalua la geometria de la bahia directamente
sobre esa malla:
  - oceano profundo (clip -600 m) al sur de la costa (y < 0)
  - bahia rectangular de 164 m:  0 <= y <= L,  |x| <= L/4   (L = 119 km)
  - tierra (0 m) en el resto (norte / flancos)
El caso 'nobay' es igual pero sin la muesca de la bahia.

Escribe (formato MITgcm, big-endian float64, x mas rapido):
  bahia_01_expand_bat.bin, bahia_01_expand_dx.bin, bahia_01_expand_dy.bin
  nobahia_01_expand_bat.bin, nobahia_01_expand_dx.bin, nobahia_01_expand_dy.bin
  bathy_5km_preview.png  (verificacion visual)

Uso:  ml load herramientas/python/3.11.8 && python3 gen_bathy_5km.py
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DT = np.dtype(">f8")
L = 119000.0          # tamano caracteristico de la bahia [m]
H_BAY = -164.0        # profundidad de la bahia [m]
H_DEEP = -600.0       # oceano profundo (clip del notebook; grid vertical ~600 m)


def build_new_domain(nx_center=96, ny=123,
                     x_min_center=-240e3, x_max_center=240e3,
                     x_min_expand=-1438e3, x_max_expand=1438e3,
                     y_min=-476e3, y_min_expand=-16762e2, y_max=139e3,
                     factor=1):
    """IDENTICO al notebook: define los vectores de la malla destino."""
    DelX = (2 * x_max_center) / nx_center
    DelY = DelX
    target_x = x_max_expand - x_max_center
    target_y = abs(y_min_expand - y_min)
    dx = [DelX]
    while sum(dx) < target_x:
        dx.append(dx[-1] * factor)
    x_off = np.cumsum(dx)
    dy = [DelY]
    while sum(dy) < target_y:
        dy.append(dy[-1] * factor)
    y_off = np.cumsum(dy)
    x_left = x_min_center - x_off[::-1]
    x_right = x_max_center + x_off
    y_expand = y_min - y_off[::-1]
    x_center = np.round(np.linspace(x_min_center, x_max_center, nx_center), 1)
    y_center = np.round(np.linspace(y_min, y_max, ny), 1)
    x_vect = np.concatenate((x_left, x_center, x_right))
    y_vect = np.concatenate((y_expand, y_center))
    return x_vect, y_vect, DelX


def grid_spacing(v):
    d = v[1:] - v[:-1]
    return np.append(d, d[-1])


def make_case(with_bay):
    # malla destino (mismo recorte que interpolate_bathy: crop_rows=12, crop_cols=8)
    x_vect, y_vect, DelX = build_new_domain()
    y_vect = y_vect[12:]
    x_vect = x_vect[8:-8]
    nx, ny = len(x_vect), len(y_vect)
    X, Y = np.meshgrid(x_vect, y_vect)          # (ny, nx)

    H = np.zeros((ny, nx))                       # tierra = 0
    H[Y < 0.0] = H_DEEP                          # oceano profundo al sur de la costa
    if with_bay:
        bay = (Y >= 0.0) & (Y <= L) & (np.abs(X) <= L / 4.0)
        H[bay] = H_BAY                           # bahia rectangular
    return x_vect, y_vect, X, Y, H, DelX


def write_bin(arr, fname):
    arr.astype(DT).tofile(fname)


def main():
    out = {}
    for tag, with_bay, pre in [("bay", True, "bahia_01_expand"),
                               ("nobay", False, "nobahia_01_expand")]:
        x_vect, y_vect, X, Y, H, DelX = make_case(with_bay)
        nx, ny = len(x_vect), len(y_vect)
        dx = grid_spacing(x_vect)
        dy = grid_spacing(y_vect)
        write_bin(H, f"{pre}_bat.bin")
        write_bin(dx, f"{pre}_dx.bin")
        write_bin(dy, f"{pre}_dy.bin")
        out[tag] = (x_vect, y_vect, H)
        print(f"[{tag}] {pre}_bat.bin  Nx={nx} Ny={ny}  "
              f"dx~{np.mean(dx):.0f} m dy~{np.mean(dy):.0f} m  "
              f"prof: deep={H.min():.0f} bay={H_BAY if with_bay else 'NA'}  "
              f"dominio x[{x_vect.min()/1e3:.0f},{x_vect.max()/1e3:.0f}]km "
              f"y[{y_vect.min()/1e3:.0f},{y_vect.max()/1e3:.0f}]km")

    # --- figura de verificacion -------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    for ax, tag in zip(axes, ["bay", "nobay"]):
        xv, yv, H = out[tag]
        pc = ax.pcolormesh(xv / 1e3, yv / 1e3, H, cmap="viridis", shading="auto")
        ax.contour(xv / 1e3, yv / 1e3, H, levels=[-300, -100], colors="k", linewidths=0.5)
        fig.colorbar(pc, ax=ax, label="profundidad [m]")
        ax.set(title=f"{tag}  (5 km, {H.shape[1]}x{H.shape[0]})",
               xlabel="x [km]", ylabel="y [km]")
    # zoom de la bahia en el primer panel
    axes[0].set_xlim(-120, 120); axes[0].set_ylim(-200, 140)
    fig.suptitle("Batimetria 5 km — caso barotropico (verificacion)")
    fig.tight_layout()
    fig.savefig("bathy_5km_preview.png", dpi=110)
    print("preview -> bathy_5km_preview.png")


if __name__ == "__main__":
    main()
