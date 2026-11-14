import shutil
import sys

import _env  # noqa: F401
import xarray as xr

src = r"C:\Users\alvar\wsl\sfincs\rootfs\data\base\sfincs_map.nc" if len(sys.argv) < 2 else sys.argv[1]
shutil.copy(src, "data/processed/_progress_map.nc")
ds = xr.open_dataset("data/processed/_progress_map.nc", decode_times=False)
print("variables:", list(ds.data_vars)[:12])
n = ds.sizes.get("time")
tt = ds["time"].values
print("map time steps written:", n, "| last simulated time: %.1f h after 28 Oct 00:00 UTC (run ends at 60 h)" % (float(tt[-1]) / 3600))
if "zs" in ds:
    print("max zs so far (m):", float(ds["zs"].isel(time=-1).max()))
