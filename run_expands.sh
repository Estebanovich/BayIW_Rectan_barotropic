#!/bin/bash
# Script para compilar, limpiar y ejecutar el modelo MITgcm
# se aplican las mismas elecciones (limpieza y MPI) para run_expand y run_expand_nobay


# --- Preguntar opciones comunes para run_expand y run_expand_nobay ---
read -p "¿Desea limpiar las carpetas run_expand y run_expand_nobay antes de correr el modelo? [y/n]: " respuesta_clean_global
read -p "¿Desea ejecutar el modelo con MPI en ambas carpetas? [y/n]: " exec_mpi_global
if [[ "$exec_mpi_global" == [yY] ]]; then
    read -p "Ingrese el número de núcleos (ejemplo: 4): " np_global
fi

# --- FASE 1: Limpieza y ejecución en 'run_expand' ---
echo "----------------------------------------"
echo "Accediendo al directorio 'run_expand'..."
cd run_expand || { echo "No se pudo acceder a 'run_expand'."; exit 1; }

if [[ "$respuesta_clean_global" == [yY] ]]; then
    echo "Limpiando archivos antiguos en 'run_expand'..."
    rm -f pickup* 2>/dev/null
    rm -rf mnc_000* 2>/dev/null
    rm -f PHref* 2>/dev/null
    rm -f RhoRef.* 2>/dev/null
    rm -f output.txt 2>/dev/null
    rm -f STDERR.0000 2>/dev/null
    rm -f mitgcmuv 2>/dev/null
    rm -f STD* 2>/dev/null
fi

echo "Copiando el nuevo ejecutable desde '../build/mitgcmuv'..."
cp ../build/mitgcmuv .
if [ $? -ne 0 ]; then
    echo "Error al copiar el ejecutable."
    exit 1
fi

echo "Estableciendo límite de archivos abiertos con 'ulimit -n 6000'..."
ulimit -n 6000

if [[ "$exec_mpi_global" == [yY] ]]; then
    echo "Ejecutando el modelo con MPI en run_expand con $np_global núcleos..."
    time mpirun -np $np_global ./mitgcmuv > output.txt &
else
    echo "Ejecutando el modelo sin MPI en run_expand..."
    time ./mitgcmuv > output.txt &
fi

pid_expand=$!
echo "El modelo en 'run_expand' se está ejecutando en segundo plano con PID $pid_expand."
echo "Esperando a que termine la ejecución en 'run_expand'..."
wait $pid_expand
echo "La ejecución en 'run_expand' ha finalizado."
cd ..

# --- FASE 2: Limpieza y ejecución en 'run_expand_nobay' ---
echo "----------------------------------------"
echo "Accediendo al directorio 'run_expand_nobay'..."
cd run_expand_nobay || { echo "No se pudo acceder al directorio 'run_expand_nobay'."; exit 1; }

if [[ "$respuesta_clean_global" == [yY] ]]; then
    echo "Limpiando archivos antiguos en 'run_expand_nobay'..."
    rm -f pickup* 2>/dev/null
    rm -rf mnc_000* 2>/dev/null
    rm -f PHref* 2>/dev/null
    rm -f RhoRef.* 2>/dev/null
    rm -f output.txt 2>/dev/null
    rm -f STDERR.0000 2>/dev/null
    rm -f mitgcmuv 2>/dev/null
    rm -f STD* 2>/dev/null
fi

echo "Copiando el ejecutable desde '../build/mitgcmuv' a 'run_expand_nobay'..."
cp ../build/mitgcmuv .
if [ $? -ne 0 ]; then
    echo "Error al copiar el ejecutable a 'run_expand_nobay'."
    exit 1
fi

echo "Estableciendo límite de archivos abiertos con 'ulimit -n 6000'..."
ulimit -n 6000

if [[ "$exec_mpi_global" == [yY] ]]; then
    echo "Ejecutando el modelo con MPI en run_expand_nobay con $np_global núcleos..."
    time mpirun -np $np_global ./mitgcmuv > output.txt &
else
    echo "Ejecutando el modelo sin MPI en run_expand_nobay..."
    time ./mitgcmuv > output.txt &
fi

pid_nobay=$!
echo "El modelo en 'run_expand_nobay' se está ejecutando en segundo plano con PID $pid_nobay."
echo "Esperando a que termine la ejecución en 'run_expand_nobay'..."
wait $pid_nobay
echo "La ejecución en 'run_expand_nobay' ha finalizado."

echo "¡Todas las simulaciones han finalizado exitosamente!"
exit 0
