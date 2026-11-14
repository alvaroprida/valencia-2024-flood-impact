#!/bin/bash
# Run inside the WSL1 "sfincs" distro: unpack the remaining image layers and smoke-test the binary.
SRC=/mnt/c/Users/alvar/Documents/github/valencia-2024-flood-impact/tools/sfincs_image
for i in 01 02 03; do
  echo "unpacking layer $i"
  tar -xzf "$SRC/layer$i.tar.gz" -C / 2>&1 | head -5
done
mkdir -p /data
echo "which sfincs: $(which sfincs)"
ls -la "$(which sfincs)"
cd /data && (timeout 20 sfincs 2>&1 | head -20)
