#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_global_and_deflate.py

1) Cose tiles MNC en un único NetCDF "global" usando gluemncbig.
2) Convierte a NetCDF4 con compresión zlib (deflate) escribiendo por variable.
3) Borra archivos RAW si se pide.

Ejemplo típico:
  python make_global_and_deflate.py \
    --state-glob "../BayIW_Rectan_linear/run_expand/mnc_00*/state.*.t*.nc" \
    --grid-glob  "../BayIW_Rectan_linear/run_expand/mnc_00*/grid.t*.nc" \
    --out-state-raw "global_state_raw.nc" \
    --out-grid-raw  "global_grid_raw.nc" \
    --out-state "global_state_deflate.nc" \
    --out-grid  "global_grid_deflate.nc" \
    --vars-state "Temp,S,Eta,U,V,W" \
    --float32 --complevel 4 --many --verbose --delete-raw
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import xarray as xr


# ──────────────────────────────────────────────────────────────────────────────
# utils
# ──────────────────────────────────────────────────────────────────────────────
def which(cmd: str):
    return shutil.which(cmd)

def run_gluemncbig(files, outfile, vars_list=None, use_64bit=False, many=False, quiet=False, verbose=False):
    exe = which("gluemncbig")
    if exe is None:
        raise FileNotFoundError("No encuentro 'gluemncbig' en PATH. Instala MITgcmutils o agrega el binario a tu PATH.")
    if not files:
        raise FileNotFoundError("No se encontraron archivos para gluemncbig.")

    cmd = [exe]
    if use_64bit:
        cmd.append("-2")
    if many:
        cmd.append("--many")
    if quiet:
        cmd.append("-q")
    if verbose:
        cmd.append("--verbose")
    if vars_list:
        cmd += ["-v", ",".join(vars_list)]
    cmd += ["-o", str(outfile)]
    cmd += list(map(str, files))

    if verbose:
        print(">> Ejecutando:", " ".join(cmd))
        print(f">> Nº de tiles: {len(files)}")
    subprocess.run(cmd, check=True)

def decode_byte_attrs_inplace(ds: xr.Dataset):
    def _to_str(x):
        if isinstance(x, (bytes, bytearray)):
            return x.decode("utf-8", errors="ignore")
        return x
    for v in list(ds.variables) + list(ds.coords):
        attrs = getattr(ds[v], "attrs", {})
        for k, val in list(attrs.items()):
            attrs[k] = _to_str(val)
        ds[v].attrs = attrs
    if hasattr(ds, "attrs"):
        for k, val in list(ds.attrs.items()):
            ds.attrs[k] = _to_str(val)

def write_netcdf4_deflate_per_variable(in_path, out_path, float32=False, complevel=4, verbose=False):
    """
    Convierte (NetCDF3 o 4) -> NetCDF4 con deflate, escribiendo por variable (append).
    """
    if verbose:
        print(f">> Abriendo {in_path} ...")
    ds = xr.open_dataset(in_path, engine="netcdf4")
    decode_byte_attrs_inplace(ds)

    unlimited_dims = []
    if "T" in ds.dims:
        unlimited_dims.append("T")

    var_names = list(ds.data_vars)
    mode = "w"
    if verbose:
        print(f">> Escribiendo (NetCDF4 deflate) → {out_path}")

    for k in var_names:
        sub = ds[[k]]
        enc_var = {"zlib": True, "complevel": complevel}
        if float32 and np.issubdtype(sub[k].dtype, np.floating) and sub[k].dtype != np.float32:
            enc_var["dtype"] = "float32"

        encoding = {k: enc_var}
        for c in sub.coords:
            if c in sub.variables:
                encoding[c] = {"zlib": True, "complevel": 1}

        # seguridad: solo claves presentes
        encoding = {n: spec for n, spec in encoding.items() if n in sub.variables}

        sub.to_netcdf(
            out_path,
            mode=mode,
            engine="netcdf4",
            encoding=encoding,
            unlimited_dims=[d for d in unlimited_dims if d in sub.dims],
            compute=True,
        )
        mode = "a"
        if verbose:
            print(f"   ✓ {k}")

    ds.close()
    if verbose:
        print(">> Listo:", out_path)

# ──────────────────────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Coser tiles con gluemncbig y comprimir a NetCDF4 deflate (por variable).")
    ap.add_argument("--state-glob", type=str, default=None, help="Patrón de tiles STATE (p.ej. '../run_expand/mnc_00*/state.*.t*.nc')")
    ap.add_argument("--grid-glob",  type=str, default=None, help="Patrón de tiles GRID  (p.ej. '../run_expand/mnc_00*/grid.t*.nc')")
    ap.add_argument("--out-state-raw", type=str, default="global_state_raw.nc", help="Salida cosida (RAW) para STATE")
    ap.add_argument("--out-grid-raw",  type=str, default="global_grid_raw.nc",  help="Salida cosida (RAW) para GRID")
    ap.add_argument("--out-state", type=str, default="global_state_deflate.nc", help="Salida comprimida NetCDF4 para STATE")
    ap.add_argument("--out-grid",  type=str, default="global_grid_deflate.nc",  help="Salida comprimida NetCDF4 para GRID")
    ap.add_argument("--vars-state", type=str, default="Temp,S,Eta,U,V,W",
                    help="Variables para STATE (coma o globs). Ej: 'Temp,S,Eta,U,V,W'")
    ap.add_argument("--vars-grid",  type=str, default=None,
                    help="Variables para GRID (coma o globs). Por defecto toma todas.")
    ap.add_argument("--many", action="store_true", help="gluemncbig --many (menos ficheros abiertos a la vez)")
    ap.add_argument("-2", "--use-64bit", action="store_true", help="gluemncbig -2 (NetCDF v3 64-bit offset)")
    ap.add_argument("--float32", action="store_true", help="Convertir variables float a float32 al comprimir")
    ap.add_argument("--complevel", type=int, default=4, help="Nivel zlib (0-9)")
    ap.add_argument("-q", "--quiet", action="store_true", help="Silenciar gluemncbig")
    ap.add_argument("--verbose", action="store_true", help="Mensajes detallados")
    ap.add_argument("--delete-raw", action="store_true", help="Borrar archivos RAW tras comprimir (recomendado)")
    ap.add_argument("--delete-tiles", action="store_true", help="Borrar directorios mnc_* tras terminar (útil si ya no los necesitas)")

    args = ap.parse_args()

    if which("gluemncbig") is None:
        print("ERROR: no encuentro 'gluemncbig' en PATH. Revisa tu instalación de MITgcmutils.", file=sys.stderr)
        sys.exit(1)

    def parse_vars(s):
        if s is None: return None
        lst = [x.strip() for x in s.split(",") if x.strip()]
        return lst if lst else None

    vars_state = parse_vars(args.vars_state)
    vars_grid  = parse_vars(args.vars_grid)

    # STATE
    if args.state_glob:
        state_files = sorted(glob.glob(args.state_glob))
        if not state_files:
            print(f"ADVERTENCIA: No se encontraron archivos para --state-glob '{args.state_glob}'")
        else:
            if args.verbose:
                print(f">> STATE tiles: {len(state_files)}")
            run_gluemncbig(
                files=state_files,
                outfile=args.out_state_raw,
                vars_list=vars_state,
                use_64bit=args.use_64bit,
                many=args.many,
                quiet=args.quiet,
                verbose=args.verbose,
            )
            write_netcdf4_deflate_per_variable(
                in_path=args.out_state_raw,
                out_path=args.out_state,
                float32=args.float32,
                complevel=args.complevel,
                verbose=args.verbose,
            )
            if args.delete_raw and Path(args.out_state_raw).exists():
                if args.verbose: print(f"🗑 Borrando RAW: {args.out_state_raw}")
                os.remove(args.out_state_raw)

    # GRID
    if args.grid_glob:
        grid_files = sorted(glob.glob(args.grid_glob))
        if not grid_files:
            print(f"ADVERTENCIA: No se encontraron archivos para --grid-glob '{args.grid_glob}'")
        else:
            if args.verbose:
                print(f">> GRID tiles: {len(grid_files)}")
            run_gluemncbig(
                files=grid_files,
                outfile=args.out_grid_raw,
                vars_list=vars_grid,
                use_64bit=args.use_64bit,
                many=args.many,
                quiet=args.quiet,
                verbose=args.verbose,
            )
            write_netcdf4_deflate_per_variable(
                in_path=args.out_grid_raw,
                out_path=args.out_grid,
                float32=args.float32,
                complevel=args.complevel,
                verbose=args.verbose,
            )
            if args.delete_raw and Path(args.out_grid_raw).exists():
                if args.verbose: print(f"🗑 Borrando RAW: {args.out_grid_raw}")
                os.remove(args.out_grid_raw)

    if not args.state_glob and not args.grid_glob:
        print("Nada que hacer: especifica al menos --state-glob o --grid-glob", file=sys.stderr)
        sys.exit(2)

    if args.delete_tiles:
        # borra mnc_* del cwd (sé prudente: corre desde la carpeta correcta)
        to_delete = [p for p in Path(".").glob("mnc_*") if p.is_dir()]
        for d in to_delete:
            if args.verbose: print(f"🗑 Borrando directorio de tiles: {d}")
            shutil.rmtree(d)

    if args.verbose:
        print("==> Terminado")

if __name__ == "__main__":
    main()
