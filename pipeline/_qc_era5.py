import _env  # noqa: F401
import xarray as xr

ds = xr.open_dataset("data/raw/era5/era5_hourly.nc")
for name, la, lo in (("Chiva/Poyo headwaters", 39.50, -0.75), ("Turis/Siete Aguas", 39.25, -0.75),
                     ("Utiel/Requena", 39.50, -1.25), ("Valencia coast", 39.50, -0.25)):
    s = ds.precip.sel(lat=la, lon=lo, method="nearest").to_series()
    d = s["2024-10-29"]
    print(f"\n{name}: 29 Oct hourly mm (UTC 00..23)")
    print(" ".join(f"{v:4.1f}" for v in d.values), "| day total", round(float(d.sum()), 1))
