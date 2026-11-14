#!/bin/bash
# Run one SFINCS model inside the WSL1 "sfincs" distro.   usage: wsl -d sfincs -- bash tools/run_sfincs.sh <run_name>
# Copies models/<run> to the Linux filesystem (much faster I/O than /mnt/c), runs it, copies the results back.
RUN=${1:-base}
SRC=/mnt/c/Users/alvar/Documents/github/valencia-2024-flood-impact/models/$RUN
DST=/data/$RUN
rm -rf "$DST" && mkdir -p /data && cp -r "$SRC" "$DST"
cd "$DST" || exit 1
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-12}
echo "start $(date)  threads=$OMP_NUM_THREADS"
sfincs > run_stdout.txt 2>&1
echo "exit code $?  end $(date)"
mkdir -p "$SRC/out"
cp -f sfincs_map.nc sfincs_his.nc sfincs_log.txt run_stdout.txt "$SRC/out/" 2>/dev/null
ls -la "$SRC/out"
