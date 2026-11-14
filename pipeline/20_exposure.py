"""Exposure: Overture buildings with an occupancy class, floors and a WorldPop population estimate.

Overture gives subtype/class for only ~20 % of the buildings and no usable construction material (<0.1 %), so:
  occupancy = Overture label where present; else majority label of the 8 nearest labelled buildings within 200 m
              ('neighbour'); else a footprint-area rule ('rule').
  population = WorldPop 2020 (constrained, 100 m) cell totals shared among the buildings of the cell,
              proportional to floor area (footprint x floors), residential first. Mass-conserving per cell.
"""
import _env  # noqa: F401
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from scipy.spatial import cKDTree

CRS = "EPSG:32630"
g = gpd.read_parquet("data/raw/overture_buildings.parquet")
g = g[~g.is_underground.fillna(False)].copy()
g = g.to_crs(CRS)
g["area_m2"] = g.geometry.area
g = g[g.area_m2 >= 15].copy()          # drop slivers / sheds
cen = g.geometry.centroid
g["x"], g["y"] = cen.x.values, cen.y.values

MAP = {  # Overture subtype / class -> occupancy
    "residential": "residential", "house": "residential", "apartments": "residential", "detached": "residential",
    "semidetached_house": "residential", "terrace": "residential", "dormitory": "residential", "bungalow": "residential",
    "commercial": "commercial", "retail": "commercial", "office": "commercial", "supermarket": "commercial",
    "hotel": "commercial", "entertainment": "commercial", "service": "commercial",
    "industrial": "industrial", "warehouse": "industrial", "factory": "industrial", "manufacture": "industrial",
    "agricultural": "agricultural", "farm": "agricultural", "barn": "agricultural", "greenhouse": "agricultural",
    "civic": "public", "education": "public", "school": "public", "public": "public", "religious": "public",
    "hospital": "public", "medical": "public", "outbuilding": "other", "garage": "other", "garages": "other",
    "shed": "other", "roof": "other", "carport": "other",
}
lab = g["class"].map(MAP).fillna(g["subtype"].map(MAP))
g["occ"], g["occ_source"] = lab, np.where(lab.notna(), "overture", None)

# Land-use-like classes cluster (residential blocks, industrial estates); shops, schools etc. do not spread.
known = g[g.occ.isin(["residential", "industrial"])]
tree = cKDTree(known[["x", "y"]].values)
unk = g.occ.isna()
d, idx = tree.query(g.loc[unk, ["x", "y"]].values, k=10, distance_upper_bound=150)
occ_known = known.occ.values
res = []
for di, ii in zip(d, idx):
    ok = np.isfinite(di)
    if ok.sum() >= 3:
        vc = pd.Series(occ_known[ii[ok]]).value_counts(normalize=True)
        res.append(vc.index[0] if vc.iloc[0] >= 0.6 else None)  # clear local majority only
    else:
        res.append(None)
g.loc[unk, "occ"] = res
g.loc[unk & g.occ.notna(), "occ_source"] = "neighbour"
rest = g.occ.isna()
g.loc[rest, "occ"] = np.where(g.loc[rest, "area_m2"] > 1500, "industrial", np.where(g.loc[rest, "area_m2"] < 20, "other", "residential"))
g.loc[rest, "occ_source"] = "rule"
# small unlabelled 'neighbour' sheds should not inherit industrial/commercial
small = (g.occ_source != "overture") & (g.area_m2 < 40)
g.loc[small, "occ"] = "other"

# floors: Overture num_floors (74 % coverage); else by occupancy median of the labelled ones
fl = g.num_floors.astype("float")
med = fl.groupby(g.occ).median()
g["floors"] = fl.fillna(g.occ.map(med)).fillna(1).clip(1, 30)
g["floors_source"] = np.where(fl.notna(), "overture", "occupancy median")

# population from WorldPop
with rasterio.open("data/raw/worldpop/esp_ppp_2020_constrained.tif") as src:
    gg = g.to_crs(src.crs)
    rows, cols = rasterio.transform.rowcol(src.transform, gg.geometry.centroid.x.values, gg.geometry.centroid.y.values)
    arr = src.read(1, masked=True)
    g["cell"] = [f"{r}_{c}" for r, c in zip(rows, cols)]
    pop = {f"{r}_{c}": float(arr[r, c]) if arr[r, c] is not np.ma.masked else 0.0 for r, c in set(zip(rows, cols))}
g["cell_pop"] = g.cell.map(pop).fillna(0)
w = g.area_m2 * g.floors
res_w = np.where(g.occ == "residential", w, 0.0)
g["w"] = np.where(g.groupby("cell").occ.transform(lambda s: (s == "residential").any()), res_w, w)
g["pop"] = g.cell_pop * g.w / g.groupby("cell").w.transform("sum").replace(0, np.nan)
g["pop"] = g["pop"].fillna(0)
print("buildings:", len(g), "| population assigned:", round(float(g["pop"].sum())), "| WorldPop total in cells:",
      round(float(sum(pop[c] for c in g.cell.unique()))))
print("occupancy:", g.occ.value_counts().to_dict())
print("source:", g.occ_source.value_counts().to_dict(), "| floors source:", g.floors_source.value_counts().to_dict())
out = g[["id", "occ", "occ_source", "area_m2", "floors", "floors_source", "pop", "geometry"]].copy()
out["id"] = out["id"].astype(str)
out.to_parquet("data/processed/buildings.parquet")
print("saved data/processed/buildings.parquet")
