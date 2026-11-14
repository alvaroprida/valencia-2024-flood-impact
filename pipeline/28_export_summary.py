"""Collect every number shown on the site into web/public/data/summary.json (no figures are hard-coded in the page text).

usage: python pipeline/28_export_summary.py [final_run] [run1 run2 ...]   (extra runs are listed as calibration variants)
"""
import glob
import json
import os
import sys

import common as c
import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from rasterio import features
from rasterio.transform import from_origin

FINAL = sys.argv[1] if len(sys.argv) > 1 else "base"
RUNS = sys.argv[1:] if len(sys.argv) > 1 else ["base"]
P = c.PROC
J = lambda f: json.load(open(f"{P}/{f}", encoding="utf-8"))
out = {"final_run": FINAL}

# ---- satellite
out["satellite"] = {"s1": J("validation_s1.json"), "s2": J("validation_s2.json")}

# ---- rainfall
g = pd.read_csv(f"{P}/rain_gauges_used.csv")
tot = g.tot.values
met = {}
for k in ("loo_A", "loo_B"):
    e = g[k].values - tot
    met[k] = dict(bias_mm=round(float(e.mean()), 1), rmse_mm=round(float(np.sqrt((e ** 2).mean())), 1),
                  r2=round(float(1 - (e ** 2).sum() / ((tot - tot.mean()) ** 2).sum()), 2))
out["rainfall"] = dict(n_gauges=int(len(g)), n_saih=int((g.src == "SAIH").sum()), n_aemet=int((g.src == "AEMET").sum()),
                       n_approx_coords=int((g.q == "approx").sum()), loo=met,
                       scatter=[[round(float(a), 0), round(float(b), 0), n, s] for a, b, n, s in zip(g.tot, g.loo_B, g.name, g.src)],
                       share_in_window=0.95)
rf = xr.open_dataset(f"{P}/rain_field.nc")
tr = from_origin(float(rf.lon.min()) - 0.005, float(rf.lat.max()) + 0.005, 0.01, 0.01)
b = gpd.read_file(f"{P}/basins.geojson")
hy, bm = {}, []
for _, r in b.iterrows():
    m = features.rasterize([(r.geometry, 1)], out_shape=(rf.sizes["lat"], rf.sizes["lon"]), transform=tr, fill=0).astype(bool)
    m = np.flipud(m)
    series = rf.precip.values[:, m].mean(1)
    hy[r["name"]] = [round(float(v), 2) for v in series]
    bm.append(dict(name=r["name"], area_km2=float(r["area_km2"]), mean_mm=round(float(series.sum()))))
out["rainfall"]["hyetograph_utc"] = dict(start="2024-10-28T01:00Z", step_h=1, values=hy)
out["rainfall"]["basin_means"] = bm
out["rainfall"]["chj_reference"] = {"Rambla del Poyo basin": 392, "Magro basin": 306, "Turia system": 142}

# ---- model and calibration runs
runs = {}
for r in dict.fromkeys(RUNS):
    f = f"{P}/validation_sfincs_{r}.json"
    if os.path.exists(f):
        runs[r] = J(os.path.basename(f))
        cfg = f"models/{r}/sfincs.inp"
        runs[r]["config_file"] = os.path.exists(cfg)
out["model"] = dict(runs=runs, variants_log=open(f"{P}/variants_log.txt", encoding="utf-8").read().splitlines() if os.path.exists(f"{P}/variants_log.txt") else [])
import re
specs = {"base": dict(cn=0, rain=1.0, man=1.0, lake=False)}
for line in out["model"]["variants_log"]:
    mm = re.search(r"== (\w+): CN (-?\d+) \| rain x([\d.]+) \| Manning x([\d.]+)", line)
    if mm:
        specs[mm.group(1)] = dict(cn=int(mm.group(2)), rain=float(mm.group(3)), man=float(mm.group(4)), lake=True)
out["model"]["specs"] = specs
if os.path.exists(f"{P}/hydrograph_{FINAL}.json"):
    out["model"]["hydrograph"] = J(f"hydrograph_{FINAL}.json")
if os.path.exists(f"{P}/ensemble_summary.json"):
    out["model"]["ensemble"] = J("ensemble_summary.json")

# ---- impact, priority, curves, buildings
out["impact"] = J(f"impact_summary_{FINAL}.json")
out["building_validation"] = J(f"validation_buildings_{FINAL}.json")
out["priority"] = J(f"priority_meta_{FINAL}.json")
pm = pd.read_csv(f"{P}/priority_municipalities_{FINAL}.csv")
out["priority"]["municipalities"] = json.loads(pm.head(25).to_json(orient="records", force_ascii=False))
cur = J("jrc_curves.json")
out["curves"] = cur

bld = gpd.read_parquet("data/processed/buildings.parquet")
raw = gpd.read_parquet("data/raw/overture_buildings.parquet")
out["exposure"] = dict(
    buildings=int(len(bld)), population=round(float(bld["pop"].sum())),
    occupancy=bld.occ.value_counts().to_dict(),
    occupancy_source=bld.occ_source.value_counts().to_dict(),
    floors_source=bld.floors_source.value_counts().to_dict(),
    overture_coverage=dict(subtype_or_class=round(float((raw.subtype.notna() | raw["class"].notna()).mean()), 3),
                           num_floors=round(float(raw.num_floors.notna().mean()), 3),
                           facade_material=round(float(raw.facade_material.notna().mean()), 4),
                           roof_material=round(float(raw.roof_material.notna().mean()), 4)),
    population_by_occ={k: round(float(v)) for k, v in bld.groupby("occ")["pop"].sum().items()},
    floor_area_km2=round(float((bld.area_m2 * bld.floors).sum()) / 1e6, 1),
)
out["gauges"] = dict(pd.read_csv(f"{P}/rain_gauges_used.csv").groupby("src").size().to_dict())
os.makedirs("web/public/data", exist_ok=True)
json.dump(out, open("web/public/data/summary.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("summary.json", round(os.path.getsize("web/public/data/summary.json") / 1e3), "kB | runs:", list(runs))
