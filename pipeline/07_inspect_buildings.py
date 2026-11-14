"""Which attributes do Overture buildings carry for occupancy / construction?"""
import _env  # noqa: F401
import geopandas as gpd

g = gpd.read_parquet("data/raw/overture_buildings.parquet")
print(len(g), list(g.columns))
for c in ["subtype", "class", "facade_material", "roof_material", "has_parts"]:
    if c in g:
        print(c, "coverage", round(g[c].notna().mean(), 3), g[c].value_counts().head(10).to_dict())
for c in ["height", "num_floors", "num_floors_underground"]:
    if c in g:
        print(c, "coverage", round(g[c].notna().mean(), 3), "median", g[c].median())
src = g["sources"].apply(lambda s: s[0]["dataset"] if s is not None and len(s) else None)
print(src.value_counts().head(8).to_dict())
