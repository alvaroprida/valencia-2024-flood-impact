"""ERA5 hourly precipitation (0.25 deg) for 28-30 Oct 2024 via the Open-Meteo archive API (ERA5 reanalysis, CC BY 4.0).

Only coordinates and dates are sent. Output: data/raw/era5/era5_hourly.nc (time, lat, lon) in mm per hour, UTC.
"""
import json
import os

import numpy as np
import requests
import xarray as xr

LON = np.arange(-1.50, 0.01, 0.25)
LAT = np.arange(38.75, 40.01, 0.25)
os.makedirs("data/raw/era5", exist_ok=True)

pts = [(la, lo) for la in LAT for lo in LON]
r = requests.get("https://archive-api.open-meteo.com/v1/archive", timeout=120, params={
    "latitude": ",".join(f"{la:.2f}" for la, _ in pts), "longitude": ",".join(f"{lo:.2f}" for _, lo in pts),
    "start_date": "2024-10-28", "end_date": "2024-10-30", "hourly": "precipitation", "models": "era5",
    "timezone": "GMT"})
r.raise_for_status()
data = r.json()
data = data if isinstance(data, list) else [data]
times = np.array(data[0]["hourly"]["time"], dtype="datetime64[ns]")
arr = np.full((len(times), len(LAT), len(LON)), np.nan, dtype="float32")
for (la, lo), d in zip(pts, data):
    arr[:, np.argmin(abs(LAT - la)), np.argmin(abs(LON - lo))] = np.array(d["hourly"]["precipitation"], dtype="float32")
ds = xr.Dataset({"precip": (("time", "lat", "lon"), arr)}, coords={"time": times, "lat": LAT, "lon": LON})
ds.precip.attrs.update(units="mm/h", long_name="ERA5 hourly precipitation")
ds.to_netcdf("data/raw/era5/era5_hourly.nc")
print("grid", len(LAT), "x", len(LON), "| hours", len(times), "| NaN share", float(np.isnan(arr).mean()))

tot = ds.precip.sum("time")
print("\nERA5 3-day total (mm) by grid cell, lat rows (north->south):")
print(np.round(tot.sortby("lat", ascending=False).values, 0))
mean = ds.precip.mean(("lat", "lon"))
h = mean.to_series()
print("\nregional-mean hourly peak:", h.idxmax(), round(float(h.max()), 2), "mm/h")
print("hours with > 0.5 mm/h (regional mean), first/last:", h[h > 0.5].index.min(), h[h > 0.5].index.max())
