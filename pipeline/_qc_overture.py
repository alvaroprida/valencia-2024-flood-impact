import _env  # noqa: F401
import geopandas as gpd

p = gpd.read_parquet("data/raw/overture_places.parquet")
tax = p.taxonomy.apply(lambda t: t if isinstance(t, dict) else {})
print("taxonomy keys sample:", list(tax.iloc[0].keys()) if len(tax) else None)
p["primary"] = tax.apply(lambda t: t.get("primary"))
p["hier"] = tax.apply(lambda t: "/".join(t.get("hierarchy", [])) if t.get("hierarchy") is not None else "")
for key in ("school", "hospital|medical|clinic|health", "fire_station|police", "nursing|retirement|assisted|elder"):
    m = p.hier.str.contains(key) | p.primary.fillna("").str.contains(key)
    print(f"\n## {key}: {int(m.sum())}")
    print(p[m].groupby("primary").size().sort_values(ascending=False).head(14).to_dict())
    print(p[m].hier.str.split("/").str[:3].str.join("/").value_counts().head(6).to_dict())
