#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

procesa_run () {
    local dir=$1
    echo "----------------------------------------"
    echo "Accediendo al directorio '$dir'..."
    cd "$dir" || { echo "No se pudo acceder a '$dir'." >&2; exit 1; }

    echo "Unificando archivos STDOUT.* en output_all.txt..."
    cat STDOUT.[0-9][0-9][0-9][0-9] > output_all.txt 2>/dev/null \
        || echo "Advertencia: no hay archivos STDOUT.*"

    echo "Ejecutando 'monitorMITgcm'..."
    ./monitorMITgcm output_all.txt
    echo "Se creó el archivo $dir/statsMIT.txt"
    cd - >/dev/null
}

procesa_run run_expand
procesa_run run_expand_nobay
echo "----------------------------------------"
echo "Fin del script de unificación y postproceso."
