#!/bin/bash


# Script modificado para compilar, limpiar y ejecutar el modelo MITgcm
# con opción de usar MPI

# --- Limpiar archvivos ---

# Preguntar si se desea limpiar la simulación anterior antes de correr el modelo
read -p "¿Desea limpiar la carpeta run_expand/ antes de correr el modelo? [y/n]: " respuesta_clean_run
if [[ "$respuesta_clean_run" == [yY] ]]; then
    echo "Limpiando archivos antiguos en 'run_expand'..."
    rm -f pickup* 2>/dev/null
    rm -rf mnc_000* 2>/dev/null
    rm -f PHref* 2>/dev/null
    rm -f RhoRef.* 2>/dev/null
    rm -f output.txt 2>/dev/null
    rm -f STDERR.0000 2>/dev/null
    rm -f STD* 2>/dev/null
    rm -f scratch* 2>/dev/null
  
fi 

# --- Copiar el nuevo ejecutable ---
echo "Copiando el nuevo ejecutable desde '../build/mitgcmuv'..."
cp ../build/mitgcmuv .
if [ $? -ne 0 ]; then
    echo "Error al copiar el ejecutable."
    exit 1
fi

# --- Ejecución del modelo ---
echo "Estableciendo límite de archivos abiertos con 'ulimit -n 6000'..."
ulimit -n 6000

# Preguntar si se desea ejecutar con MPI
read -p "¿Desea ejecutar el modelo con MPI? [y/n]: " exec_mpi
if [[ "$exec_mpi" == [yY] ]]; then
    read -p "Ingrese el número de núcleos (ejemplo: 4): " np
    echo "Ejecutando el modelo con MPI en $np núcleos..."
    time mpirun -np $np ./mitgcmuv > output.txt &
else
    echo "Ejecutando el modelo sin MPI..."
    time ./mitgcmuv > output.txt &
fi

if [ $? -eq 0 ]; then
    echo "El modelo se está ejecutando en segundo plano. Revisa 'output.txt' para ver la salida."
else
    echo "Error al ejecutar el modelo."
    exit 1
fi

exit 0
