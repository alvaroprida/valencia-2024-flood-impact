"""MITECO national SAIH layers (rain gauges, river gauges, reservoirs) for the Júcar area.

The ministry's download page has a captcha, so the three zips are saved manually from
https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/agua/capas-saih.html into data/raw/saih/ :
capassaih-pluviometria.zip, capassaih-rios.zip, capassaih-embalses.zip
Source: (c) Ministerio para la Transición Ecológica y el Reto Demográfico.
"""
import os
import zipfile

import _env  # noqa: F401
import geopandas as gpd

BBOX = (-1.6, 38.7, -0.0, 39.9)  # lon/lat window around the Poyo, Magro, Turia and lower Júcar

for name in ("pluviometria", "rios", "embalses"):
    z = f"data/raw/saih/capassaih-{name}.zip"
    if not os.path.exists(z):
        print(f"missing {z}")
        continue
    d = f"data/raw/saih/{name}"
    os.makedirs(d, exist_ok=True)  # each archive in its own folder
    zipfile.ZipFile(z).extractall(d)
    shp = [f for f in os.listdir(d) if f.lower().endswith(".shp")]
    g = gpd.read_file(f"{d}/{shp[0]}")
    print(f"\n## {name}: {shp[0]}  n={len(g)}  crs={g.crs}")
    print("   columns:", [c for c in g.columns if c != "geometry"])
    ll = g.to_crs(4326)
    sel = g[(ll.geometry.x > BBOX[0]) & (ll.geometry.x < BBOX[2]) & (ll.geometry.y > BBOX[1]) & (ll.geometry.y < BBOX[3])]
    print("   in Valencia window:", len(sel))
    print(sel.drop(columns="geometry").head(8).to_string())
