#!/bin/bash
#==============================================================================
# submit_2stage_barotropic.slurm
# Corrida completa en 2 etapas del caso BAROTROPICO (densidad constante)
#   - run_expand        (con bahia)
#   - run_expand_nobay  (control sin bahia)
#
# Etapa 1 (forzada):  startTime=0      -> endTime=216000 s (~2.5 d), nIter0=0
#                     viento periodico ON, lee T barotropico (T=33.6 uniforme),
#                     escribe el checkpoint permanente pickup.ckptA
# Etapa 2 (libre):    startTime=216000 -> endTime=432000 s (~5 d),  nIter0=7200
#                     reinicia desde pickup.ckptA, viento OFF
#
# Requiere el ejecutable ya compilado en build/mitgcmuv (MPI, SIZE.h 2x2 = 4 ranks).
# Compilacion previa:
#   source /LUSTRE/HOME/esteban/MITgcm/setup_env.sh
#   cd build && ../../../tools/genmake2 -mods=../code -mpi -of=$MITGCM_OF
#   make depend && make -j 4
#
# Envio:  sbatch submit_2stage_barotropic.slurm
#==============================================================================
#SBATCH --job-name=BayIW_barotropic
#SBATCH --partition=id
#SBATCH --nodes=1
#SBATCH --ntasks=4                 # = nPx*nPy de SIZE.h (2x2)
#SBATCH --cpus-per-task=1
#SBATCH --time=2-00:00:00
#SBATCH --output=/LUSTRE/HOME/esteban/MITgcm/verification/BayIW_Rectan_barotropic/logs/%x_%j.log
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=estebanci@atmosfera.unam.mx

set -euo pipefail

EXP=/LUSTRE/HOME/esteban/MITgcm/verification/BayIW_Rectan_barotropic
NP=${SLURM_NTASKS:-4}

# --- Entorno Intel (ifort + Intel MPI 2021.5 + NetCDF 4.4.1.1) --------------
source /LUSTRE/HOME/esteban/MITgcm/setup_env.sh
ulimit -n 6000 || true

EXE=$EXP/build/mitgcmuv
if [[ ! -x "$EXE" ]]; then
    echo "ERROR: no existe el ejecutable $EXE"
    echo "       Compila primero el modelo con MPI (ver cabecera de este script)."
    exit 1
fi

# ---------------------------------------------------------------------------
# Ejecuta una etapa en un run dir:  run_stage <run_dir> <tag> <archivo_data>
# ---------------------------------------------------------------------------
run_stage () {
    local dir=$1 tag=$2 dataf=$3
    echo "-------------------------------------------------------------------"
    echo ">>> $(basename "$dir") — $tag   inicio: $(date)"
    cd "$dir"
    cp -f "$EXE" .
    cp -f "$dataf" data
    rm -f STDOUT.* STDERR.* "output_${tag}.txt" 2>/dev/null || true

    time mpirun -n "$NP" ./mitgcmuv > "output_${tag}.txt" 2>&1

    if ! grep -q "NORMAL END" "output_${tag}.txt"; then
        echo "ERROR: $(basename "$dir") $tag NO termino con NORMAL END"
        echo "----- ultimas lineas de output_${tag}.txt -----"
        tail -40 "output_${tag}.txt"
        exit 2
    fi
    # chequeo barotropico: la temperatura debe seguir uniforme (=33.6)
    local tmin tmax
    tmax=$(grep "dynstat_theta_max" STDOUT.0000 2>/dev/null | tail -1 | awk '{print $NF}')
    tmin=$(grep "dynstat_theta_min" STDOUT.0000 2>/dev/null | tail -1 | awk '{print $NF}')
    echo "    theta_min/max final = ${tmin:-NA} / ${tmax:-NA}  (esperado 3.36E+01 constante)"
    echo "<<< $(basename "$dir") — $tag   fin: $(date)"
}

# ---------------------------------------------------------------------------
for DIR in "$EXP/run_expand" "$EXP/run_expand_nobay"; do
    echo "==================================================================="
    echo "### CASO: $(basename "$DIR") ###"
    cd "$DIR"

    # limpieza previa (solo al inicio del caso, NO entre etapas)
    rm -f pickup* output*.txt STDOUT.* STDERR.* PHref* RhoRef.* 2>/dev/null || true
    rm -rf mnc_* OUT_stage1 2>/dev/null || true

    # ---- ETAPA 1: forzada, escribe pickup.ckptA --------------------------
    run_stage "$DIR" stage1 "$DIR/data.stage1"
    if ! ls "$DIR"/pickup.ckptA.data >/dev/null 2>&1; then
        echo "ERROR: la etapa 1 en $(basename "$DIR") no produjo pickup.ckptA"
        exit 3
    fi
    # preservar la salida NetCDF de la etapa 1 antes de correr la etapa 2
    mkdir -p OUT_stage1
    for m in mnc_*; do [ -e "$m" ] && mv "$m" OUT_stage1/; done

    # ---- ETAPA 2: libre, restart desde ckptA, viento OFF -----------------
    run_stage "$DIR" stage2 "$DIR/data.stage2"
    mkdir -p OUT_stage2
    for m in mnc_*; do [ -e "$m" ] && mv "$m" OUT_stage2/; done

    echo "### $(basename "$DIR"): 2 etapas COMPLETAS ###"
done

echo "==================================================================="
echo "TODAS LAS SIMULACIONES (con y sin bahia, 2 etapas) FINALIZADAS: $(date)"
