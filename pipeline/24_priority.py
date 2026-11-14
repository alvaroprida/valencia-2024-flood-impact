"""Prioritisation of emergency response: rank 250 m cells and municipalities.

usage: python pipeline/24_priority.py [run_name]
score = 0.45 * severity-weighted people (pctile) + 0.20 * building loss (pctile)
      + 0.20 * flooded critical facilities (weighted, pctile) + 0.15 * road access cut (share of road length >= 0.3 m)
people are the ground-level-adjusted estimate (pop / floors) weighted by depth: 0.25 (0.1-0.5 m), 0.6 (0.5-1 m), 1.0 (>= 1 m).
Facility weights: hospital / care home 3, fire & police 3, school 2.
A weight-sensitivity test (500 random weight sets) reports how stable the top-ranked cells are.
"""
import json
import sys

import common as c
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from shapely.geometry import box

RUN = sys.argv[1] if len(sys.argv) > 1 else "base"
W = dict(people=0.45, loss=0.20, facility=0.20, access=0.15)
FW = {"hospital": 3, "care": 3, "fire_police": 3, "school": 2}

b = pd.read_parquet(f"{c.PROC}/impact_cells_input_{RUN}.parquet")
fac = gpd.read_parquet(f"{c.PROC}/impact_facilities_{RUN}.parquet").to_crs(c.CRS)
rd = gpd.read_parquet(f"{c.PROC}/impact_roads_{RUN}.parquet")

w_depth = np.select([b.depth >= 1.0, b.depth >= 0.5, b.depth >= 0.1], [1.0, 0.6, 0.25], 0.0)
b["people_sev"] = b.pop_ground * w_depth
cell = b.groupby(["cx", "cy"]).agg(people_all=("pop", "sum"), people_ground_exposed=("pop_ground", lambda x: x[b.loc[x.index, "flooded"]].sum()),
                                   people_severity=("people_sev", "sum"), buildings=("id", "size"),
                                   buildings_flooded=("flooded", "sum"), loss_eur=("loss_eur", "sum"),
                                   max_depth=("depth", "max"), municipality=("municipality", lambda x: x.mode().iloc[0] if x.notna().any() else None)).reset_index()

fac["cx"], fac["cy"] = (np.floor(fac.geometry.x / 250) * 250 + 125).astype(int), (np.floor(fac.geometry.y / 250) * 250 + 125).astype(int)
fl = fac[fac.flooded].assign(w=lambda x: x.facility.map(FW))
fcell = fl.groupby(["cx", "cy"]).agg(facility_score=("w", "sum"), facilities_flooded=("name", lambda x: "; ".join(map(str, x.dropna().head(4))))).reset_index()
rcell = rd.groupby(["cx", "cy"]).apply(lambda d: pd.Series(dict(road_km=d.len_m.sum() / 1e3, road_cut_share=d.loc[d.cut, "len_m"].sum() / max(d.len_m.sum(), 1))), include_groups=False).reset_index()
cell = cell.merge(fcell, how="left", on=["cx", "cy"]).merge(rcell, how="left", on=["cx", "cy"])
cell[["facility_score", "road_cut_share", "road_km"]] = cell[["facility_score", "road_cut_share", "road_km"]].fillna(0)
cell["facilities_flooded"] = cell.facilities_flooded.fillna("")
aff = cell[(cell.people_severity > 0) | (cell.loss_eur > 0) | (cell.facility_score > 0)].copy()

pct = lambda s: s.rank(pct=True)
comp = pd.DataFrame(dict(people=pct(aff.people_severity), loss=pct(aff.loss_eur), facility=np.where(aff.facility_score > 0, pct(aff.facility_score), 0.0),
                         access=aff.road_cut_share.clip(0, 1)), index=aff.index)
for k in W:  # component scores (0-1), kept so the site can re-weight them in the browser
    aff[f"c_{k}"] = comp[k].round(3)
aff["score"] = sum(W[k] * comp[k] for k in W) * 100
aff["rank"] = aff.score.rank(ascending=False, method="first").astype(int)
n = len(aff)
aff["tier"] = np.select([aff["rank"] <= max(1, int(0.05 * n)), aff["rank"] <= int(0.20 * n)], [1, 2], 3)

# sensitivity to the weights
rng = np.random.default_rng(1)
top = set(aff.nsmallest(int(0.05 * n), "rank").index)
overlap, rho = [], []
for _ in range(500):
    w = rng.dirichlet(np.ones(4))
    sc = sum(wi * comp[k] for wi, k in zip(w, W))
    t = set(sc.nlargest(len(top)).index)
    overlap.append(len(t & top) / len(top))
    rho.append(spearmanr(sc, aff.score)[0])
sens = dict(cells_ranked=n, top5pct_cells=len(top), median_overlap_of_top5pct=round(float(np.median(overlap)), 2),
            p10_overlap=round(float(np.percentile(overlap, 10)), 2), median_rank_correlation=round(float(np.median(rho)), 2))
print("sensitivity:", sens)

# cell polygons (WGS84) and municipality ranking
aff["geometry"] = [box(x - 125, y - 125, x + 125, y + 125) for x, y in zip(aff.cx, aff.cy)]
g = gpd.GeoDataFrame(aff, geometry="geometry", crs=c.CRS).to_crs(4326)
g.to_parquet(f"{c.PROC}/priority_cells_{RUN}.parquet")
mun = (aff.groupby("municipality").agg(cells=("rank", "size"), tier1_cells=("tier", lambda x: int((x == 1).sum())), people_severity=("people_severity", "sum"),
       people_exposed=("people_ground_exposed", "sum"), loss_meur=("loss_eur", lambda x: x.sum() / 1e6), score=("score", "mean"), top_score=("score", "max"),
       facilities=("facility_score", "sum")).round(2).sort_values("people_severity", ascending=False))
mun.to_csv(f"{c.PROC}/priority_municipalities_{RUN}.csv")
json.dump(dict(weights=W, facility_weights=FW, sensitivity=sens), open(f"{c.PROC}/priority_meta_{RUN}.json", "w"), indent=1)
print(mun.head(12).to_string())
print("\ntop 10 cells:")
print(aff.nsmallest(10, "rank")[["rank", "municipality", "people_ground_exposed", "loss_eur", "facilities_flooded", "road_cut_share", "max_depth", "score"]].round(2).to_string(index=False))
