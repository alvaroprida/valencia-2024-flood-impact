import _env  # noqa: F401
import geopandas as gpd
import pandas as pd

b = pd.read_parquet("data/processed/buildings.parquet")
print(pd.crosstab(b.occ, b.occ_source))
o = gpd.read_parquet("data/raw/overture_buildings.parquet")
print("\nraw Overture class values (top 25):")
print(o["class"].value_counts().head(25).to_dict())
print("raw subtype:", o["subtype"].value_counts().head(12).to_dict())
