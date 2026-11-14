"""Impact: flood depth at every building -> damage ratio (JRC Europe curves), loss, people exposed.

usage: python pipeline/23_impact.py [run_name]
  depth      = maximum modelled depth within ~25 m of the building centroid (SFINCS, 30 m)
  ratio      = JRC Europe depth-damage fraction(depth) x min(1, ceil(depth / 3 m) / floors)
               (only the storeys reached by the water are damaged: a 5-storey block flooded 1 m loses 1/5 of the curve)
  value      = JRC maximum damage for Spain (EUR/m2, 2010 prices, structure + content) x footprint x floors
  loss       = ratio x value          (2010 prices; NOT inflated to 2024)
  people     = WorldPop-based estimate per building (see 20_exposure.py); 'ground' = pop / floors
Also scores the building result against the CEMS EMSR773 building damage grades (Horta Sud, AOI03).
"""
import json
import sys

import common as c
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from shapely.geometry import Point

RUN = sys.argv[1] if len(sys.argv) > 1 else "base"
HMIN = 0.10

# ---------------------------------------------------------------- depth at buildings
depth = np.nan_to_num(c.load(f"sfincs_{RUN}_depth10.tif"), nan=0.0)
dmax = ndi.maximum_filter(depth, size=5)  # ~25 m reach around the centroid
inv = ~c.TRANSFORM
b = gpd.read_parquet("data/processed/buildings.parquet")
cen = b.geometry.centroid
col, row = inv * (cen.x.values, cen.y.values)
col, row = np.floor(col).astype(int), np.floor(row).astype(int)
ok = (col >= 0) & (col < c.W) & (row >= 0) & (row < c.H)
b["depth"] = 0.0
b.loc[ok, "depth"] = dmax[row[ok], col[ok]]
b["in_grid"] = ok

# ---------------------------------------------------------------- damage
J = json.load(open("data/processed/jrc_curves.json"))
curves = {k: (np.array(v["depth_m"]), np.array(v["damage_fraction"])) for k, v in J["curves"].items() if not np.isnan(v["damage_fraction"][0])}
MAXD = J["max_damage_spain_eur_m2_2010"]
CURVE = {"residential": "Residential buildings", "commercial": "Commercial buildings", "industrial": "Industrial buildings",
         "public": "Commercial buildings", "agricultural": "Agriculture", "other": "Commercial buildings"}
VALUE = {"residential": MAXD["Residential buildings"]["total"], "commercial": MAXD["Commercial buildings"]["total"],
         "industrial": MAXD["Industrial buildings"]["total"], "public": MAXD["Commercial buildings"]["total"],
         "agricultural": MAXD["Industrial buildings"]["total"] * 0.5, "other": MAXD["Commercial buildings"]["total"] * 0.25}


def frac(row_occ, d):
    x, y = curves[CURVE[row_occ]]
    return np.interp(d, x, y)


b["frac"] = 0.0
for occ in CURVE:
    m = b.occ == occ
    b.loc[m, "frac"] = frac(occ, b.loc[m, "depth"].values)
storeys = np.minimum(1.0, np.ceil(np.maximum(b.depth, 1e-6) / 3.0) / b.floors)
b["ratio"] = np.where(b.depth >= HMIN, b.frac * storeys, 0.0)
b["value_eur"] = b.occ.map(VALUE) * b.area_m2 * b.floors
b["loss_eur"] = b.ratio * b.value_eur
b["flooded"] = b.depth >= HMIN
b["pop_ground"] = b["pop"] / b.floors
b["dclass"] = pd.cut(b.ratio, [-1, 0, 0.1, 0.3, 0.6, 1.01], labels=["none", "minor", "moderate", "major", "severe"])

# ---------------------------------------------------------------- municipality, 250 m cell
cen_gdf = gpd.GeoDataFrame(b[["id"]], geometry=cen.values, crs=c.CRS)
div = gpd.read_parquet("data/raw/overture_divisions.parquet")
div = div[div.subtype == "locality"].copy()
div["municipality"] = div.names.apply(lambda n: n.get("primary") if n else None)
div = div.to_crs(c.CRS)[["municipality", "geometry"]].reset_index(drop=True)
# Overture 'locality' mixes municipalities with comarcas: drop polygons that contain other localities
div = div[~div.municipality.fillna("").str.startswith("Comarca")].reset_index(drop=True)
rp = div.geometry.representative_point()
n_inside = np.array([sum(div.geometry.iloc[i].contains(rp.iloc[j]) for j in range(len(div)) if j != i) for i in range(len(div))])
div = div[n_inside < 2].reset_index(drop=True)
print("municipalities kept:", len(div))
div.to_file(f"{c.PROC}/municipalities.gpkg", driver="GPKG")
j = gpd.sjoin(cen_gdf, div, how="left", predicate="within").drop_duplicates("id")
b["municipality"] = j.set_index("id").reindex(b.id).municipality.values
b["cx"], b["cy"] = (np.floor(cen.x / 250) * 250 + 125).astype(int), (np.floor(cen.y / 250) * 250 + 125).astype(int)

# ---------------------------------------------------------------- critical facilities and roads
p = gpd.read_parquet("data/raw/overture_places.parquet").to_crs(c.CRS)
tax = p.taxonomy.apply(lambda t: (t.get("primary") if isinstance(t, dict) else "") or "")
# strict category lists (language, driving, music, art, sports and other specialty schools, dental and other private clinics
# are NOT critical facilities)
KEY = {
    "hospital": {"hospital", "public_health_clinic", "urgent_care_clinic", "emergency_room", "medical_center"},
    "school": {"school", "elementary_school", "preschool", "high_school", "private_school", "public_school", "day_care_preschool",
               "vocational_and_technical_school", "middle_school", "kindergarten", "college_university", "university", "secondary_school"},
    "fire_police": {"police_station", "fire_station"},
    "care": {"retirement_home", "assisted_living_facility"},
}
p["facility"] = None
for k, vals in KEY.items():
    p.loc[tax.isin(vals) & p.facility.isna(), "facility"] = k
fac = p[p.facility.notna()].copy()
fac["name"] = fac.names.apply(lambda n: n.get("primary") if n else None)
colf, rowf = inv * (fac.geometry.x.values, fac.geometry.y.values)
colf, rowf = np.clip(np.floor(colf).astype(int), 0, c.W - 1), np.clip(np.floor(rowf).astype(int), 0, c.H - 1)
fac["depth"] = dmax[rowf, colf]
fac["flooded"] = fac.depth >= HMIN
fac = fac.to_crs(4326)

s = gpd.read_parquet("data/raw/overture_segments.parquet")
s = s[(s.subtype == "road") & s["class"].isin(["motorway", "trunk", "primary", "secondary", "tertiary", "residential", "unclassified", "service"])].to_crs(c.CRS)
L = s.geometry.length.values
mx = np.zeros(len(s))
for f in (0.0, 0.25, 0.5, 0.75, 1.0):
    pts = s.geometry.interpolate(f, normalized=True)
    cc, rr = inv * (pts.x.values, pts.y.values)
    cc, rr = np.clip(np.floor(cc).astype(int), 0, c.W - 1), np.clip(np.floor(rr).astype(int), 0, c.H - 1)
    mx = np.maximum(mx, dmax[rr, cc])
s["depth"] = mx
s["len_m"] = L
mid = s.geometry.interpolate(0.5, normalized=True)
s["cx"], s["cy"] = (np.floor(mid.x / 250) * 250 + 125).astype(int), (np.floor(mid.y / 250) * 250 + 125).astype(int)
s["cut"] = s.depth >= 0.30  # roughly the limit for ordinary vehicles; rescue trucks cope with more

# ---------------------------------------------------------------- aggregates
summary = dict(
    run=RUN, buildings_total=int(len(b)), buildings_flooded=int(b.flooded.sum()),
    people_in_flooded_buildings=round(float(b.loc[b.flooded, "pop"].sum())),
    people_ground_exposed=round(float(b.loc[b.flooded, "pop_ground"].sum())),
    people_in_buildings_over_50cm=round(float(b.loc[b.depth >= 0.5, "pop"].sum())),
    people_in_buildings_over_1m=round(float(b.loc[b.depth >= 1.0, "pop"].sum())),
    loss_eur_2010=round(float(b.loss_eur.sum())), road_km_flooded_over_30cm=round(float(s.loc[s.cut, "len_m"].sum()) / 1e3, 1),
    facilities_flooded={k: int(((fac.facility == k) & fac.flooded).sum()) for k in KEY},
    by_occupancy={o: dict(flooded=int((b.flooded & (b.occ == o)).sum()), loss_meur=round(float(b.loc[b.occ == o, "loss_eur"].sum()) / 1e6, 1))
                  for o in CURVE},
    by_damage_class={str(k): int(v) for k, v in b.dclass.value_counts().items()},
)
muni = (b[b.flooded].groupby("municipality").agg(buildings=("id", "size"), people=("pop", "sum"), people_ground=("pop_ground", "sum"),
        loss_meur=("loss_eur", lambda x: x.sum() / 1e6), mean_depth=("depth", "mean"), max_depth=("depth", "max")).round(2))
tot = b.groupby("municipality").agg(buildings_all=("id", "size"), people_all=("pop", "sum"))
muni = muni.join(tot).assign(share_buildings=lambda x: (x.buildings / x.buildings_all).round(3)).sort_values("people", ascending=False)
summary["top_municipalities_by_people"] = muni.head(12).reset_index().to_dict("records")
json.dump(summary, open(f"{c.PROC}/impact_summary_{RUN}.json", "w"), indent=1, default=str)

b[b.flooded | (b.depth > 0)].drop(columns=["in_grid"]).to_parquet(f"{c.PROC}/impact_buildings_{RUN}.parquet")
muni.to_csv(f"{c.PROC}/impact_municipalities_{RUN}.csv")
fac.drop(columns=["names", "websites", "emails", "socials", "phones", "brand", "addresses", "sources", "taxonomy"], errors="ignore").to_parquet(f"{c.PROC}/impact_facilities_{RUN}.parquet")
s[["id", "class", "len_m", "depth", "cx", "cy", "cut", "geometry"]].to_parquet(f"{c.PROC}/impact_roads_{RUN}.parquet")
b[["id", "cx", "cy", "flooded", "pop", "pop_ground", "loss_eur", "ratio", "depth", "occ", "municipality"]].to_parquet(f"{c.PROC}/impact_cells_input_{RUN}.parquet")

print(json.dumps({k: v for k, v in summary.items() if k != "top_municipalities_by_people"}, indent=1, default=str))
print(muni.head(10).to_string())

# ---------------------------------------------------------------- compare with CEMS building grades (Horta Sud)
g = gpd.read_file("data/raw/cems/EMSR773_AOI03_GRA_PRODUCT_v2/x/EMSR773_AOI03_GRA_PRODUCT_builtUpP_v2.shp").to_crs(c.CRS)
bc_ = gpd.GeoDataFrame(b[["id", "depth", "ratio", "occ"]], geometry=cen.values, crs=c.CRS)
jj = gpd.sjoin_nearest(g[["damage_gra", "geometry"]], bc_, how="left", max_distance=30, distance_col="d").dropna(subset=["id"])
jj = jj.drop_duplicates(subset=["geometry"])
rep = {}
for grade, sub in jj.groupby("damage_gra"):
    rep[grade] = dict(n=int(len(sub)), median_depth_m=round(float(sub.depth.median()), 2), share_modelled_flooded=round(float((sub.depth >= HMIN).mean()), 3),
                      median_ratio=round(float(sub.ratio.median()), 3))
print("\nCEMS building damage grade vs modelled depth (matched within 30 m):")
print(json.dumps(rep, indent=1))
json.dump(rep, open(f"{c.PROC}/validation_buildings_{RUN}.json", "w"), indent=1)
