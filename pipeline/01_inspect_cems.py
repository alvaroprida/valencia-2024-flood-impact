"""Print attributes, CRS and extent of the downloaded CEMS EMSR773 layers."""
import glob

import _env  # noqa: F401  (must come before geopandas)
import geopandas as gpd

ROOT = "data/raw/cems"

for f in sorted(glob.glob(f"{ROOT}/*/x/*.shp")):
    if "areaOfInterest" in f:
        continue
    g = gpd.read_file(f)
    name = f.split("\\")[-1].replace("EMSR773_", "")
    print(f"\n## {name}  n={len(g)}  crs={g.crs.to_epsg()}  bounds={[round(b, 3) for b in g.to_crs(4326).total_bounds]}")
    cols = [c for c in g.columns if c != "geometry"]
    print("   cols:", cols)
    for c in cols:
        if g[c].dtype == object and g[c].nunique() <= 12:
            print(f"   {c}: {g[c].value_counts().to_dict()}")
    if "floodDepth" in f:
        for c in cols:
            if g[c].dtype != object and c not in ("area",):
                print(f"   {c}: min={g[c].min()} max={g[c].max()}")
