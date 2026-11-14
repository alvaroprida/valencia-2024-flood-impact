"""Merge SAIH station geometry (MITECO 2014 layers), CHJ event totals / peaks and AEMET stations into one GeoJSON.

coord_quality: 'exact' = station geometry from the MITECO SAIH layer or the AEMET inventory;
               'approx' = municipality centre (gauge named in the CHJ report but absent from the 2014 layer).
"""
import json
import re
import unicodedata

import _env  # noqa: F401
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

BBOX = (-1.6, 38.7, -0.0, 39.9)
STOP = {"DE", "DEL", "LA", "EL", "EN", "LAS", "LOS", "I", "D"}


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s.replace("-", " "))
    return [w for w in s.split() if w not in STOP]


def contains(hay, needle):
    n = len(needle)
    return n > 0 and any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def load_layer(name, shp):
    g = gpd.read_file(f"data/raw/saih/{name}/{shp}").to_crs(4326)
    g = g[(g.geometry.x > BBOX[0]) & (g.geometry.x < BBOX[2]) & (g.geometry.y > BBOX[1]) & (g.geometry.y < BBOX[3])]
    g["name"] = g.IDPUNTO.str.replace(r"^(PLUVIO|AFORO|EMBALSE)\s+", "", regex=True).str.strip()
    g["tokens"] = g["name"].apply(norm)
    return g


rain, flow, res = load_layer("pluviometria", "Pluviometria.shp"), load_layer("rios", "Caudales.shp"), load_layer("embalses", "Embalses.shp")
chj = json.load(open("data/processed/chj_rain_gauges.json", encoding="utf-8"))
feats = []

# --- rain gauges: SAIH layer, event total from the CHJ report where the names match
used = set()
for r in chj:
    hay = norm(r["text"])
    cands = [(len(g.tokens), i) for i, g in rain.iterrows() if contains(hay, g.tokens)]
    if cands:
        _, i = max(cands)
        g = rain.loc[i]
        if i in used and g["name"] != "VALENCIA":
            pass
        used.add(i)
        feats.append(dict(kind="rain", name=g["name"].title(), event_mm=r["mm"], report_text=r["text"],
                          coord_quality="exact", source="MITECO SAIH layer", geometry=g.geometry))
    elif r["lat"] is not None:
        feats.append(dict(kind="rain", name=r["text"], event_mm=r["mm"], report_text=r["text"],
                          coord_quality="approx", source=f"municipality centre ({r['municipality']})",
                          geometry=Point(r["lon"], r["lat"])))
for i, g in rain.iterrows():
    if i not in used:
        feats.append(dict(kind="rain", name=g["name"].title(), event_mm=None, report_text=None,
                          coord_quality="exact", source="MITECO SAIH layer", geometry=g.geometry))

# --- AEMET stations with the daily total of 29 Oct (exact coordinates)
inv = {s["indicativo"]: s for s in json.load(open("data/raw/aemet/inventory.json", encoding="utf-8"))}
dms = lambda v: (-1 if v[-1] in "WS" else 1) * (int(v[:2]) + int(v[2:4]) / 60 + int(v[4:6]) / 3600)
for d in json.load(open("data/raw/aemet/daily_20241027_20241101.json", encoding="utf-8")):
    if d["fecha"] != "2024-10-29" or d.get("prec") in (None, "Ip") or d["indicativo"] not in inv:
        continue
    s = inv[d["indicativo"]]
    lat, lon = dms(s["latitud"]), dms(s["longitud"])
    if BBOX[0] < lon < BBOX[2] and BBOX[1] < lat < BBOX[3]:
        feats.append(dict(kind="rain_aemet", name=d["nombre"].title(), event_mm=float(d["prec"].replace(",", ".")),
                          report_text="AEMET daily total, 29 Oct 2024", coord_quality="exact",
                          source="AEMET OpenData", geometry=Point(lon, lat)))

# --- discharge: SAIH river gauges, peaks from the CHJ report table (29-30 Oct 2024)
PEAKS = {  # layer name -> (river, peak m3/s, time, note)
    "RAMBLA POYO": ("Rambla del Poyo", 2282.9, "29 Oct 18:55", "last reading before the sensor was lost"),
    "VILAMARXANT": ("Turia", 1946.2, "30 Oct 02:25", ""),
    "LA PRESA": ("Turia (Manises)", 1756.3, "29 Oct 22:35", "last reading before the sensor was lost"),
    "REPARTIMENT": ("Turia (Quart de Poblet)", 2031.0, "30 Oct 04:35", ""),
    "RAM. CASTELLANA": ("Rambla Castellana", 263.7, "29 Oct 21:05", ""),
    "HUERTO MULET": ("Júcar (Algemesí)", 1523.0, "30 Oct 03:35", ""),
    "CULLERA": ("Júcar (Sueca)", 1176.0, "30 Oct 05:00", ""),
    "LORIGUILLA": ("Turia, Loriguilla reservoir inflow", 713.5, "30 Oct 02:10", ""),
    "GUADASSUAR": ("Magro (Guadassuar)", None, "29 Oct 20:50", "level 5.47 m, last reading before the sensor was lost"),
}
for _, g in flow.iterrows():
    p = PEAKS.get(g["name"])
    feats.append(dict(kind="discharge", name=g["name"].title(), event_mm=None,
                      report_text=(f"{p[0]}: peak {p[1]} m3/s at {p[2]} {p[3]}".strip() if p and p[1] else (f"{p[0]}: {p[3]}" if p else None)),
                      peak_q=p[1] if p else None, peak_time=p[2] if p else None,
                      coord_quality="exact", source="MITECO SAIH layer", geometry=g.geometry))
for _, g in res.drop_duplicates("name").iterrows():
    feats.append(dict(kind="reservoir", name=g["name"].title(), event_mm=None, report_text=None,
                      coord_quality="exact", source="MITECO SAIH layer", geometry=g.geometry))

out = gpd.GeoDataFrame(pd.DataFrame(feats), geometry="geometry", crs=4326)
out.to_file("data/processed/gauges.geojson", driver="GeoJSON")
print(out.groupby(["kind", "coord_quality"]).size())
print("\nmatched peaks:", sorted(set(out[out.peak_q.notna()].name)))
print("peak entries without a layer geometry:", [k for k in PEAKS if k not in set(flow["name"])])
print("rain gauges with event total:", int(out[out.kind == "rain"].event_mm.notna().sum()),
      "| approx-only:", int(((out.kind == "rain") & (out.coord_quality == "approx")).sum()))
print(out[(out.kind == "rain") & out.event_mm.notna()].sort_values("event_mm", ascending=False)[["name", "event_mm", "coord_quality"]].head(8).to_string(index=False))
