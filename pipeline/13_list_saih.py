"""List every SAIH rain and river gauge inside the Valencia window with coordinates."""
import _env  # noqa: F401
import geopandas as gpd

BBOX = (-1.6, 38.7, -0.0, 39.9)
for name, shp in (("pluviometria", "Pluviometria.shp"), ("rios", "Caudales.shp")):
    g = gpd.read_file(f"data/raw/saih/{name}/{shp}").to_crs(4326)
    g = g[(g.geometry.x > BBOX[0]) & (g.geometry.x < BBOX[2]) & (g.geometry.y > BBOX[1]) & (g.geometry.y < BBOX[3])]
    col = "DESCRIPCIO" if "DESCRIPCIO" in g else "IDPUNTO"
    print(f"\n## {name} ({len(g)})")
    for _, r in g.sort_values("IDPUNTO").iterrows():
        print(f"{r.IDPUNTO.strip():38s} {r.geometry.x:8.4f} {r.geometry.y:8.4f}  {r.TIPO}")
