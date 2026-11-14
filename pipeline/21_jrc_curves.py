"""Export the JRC global flood depth-damage functions (Huizinga et al. 2017, EUR 28552 EN) for Europe and Spain.

Output data/processed/jrc_curves.json:
  curves[class] = {depth_m, damage_fraction (Europe), std (Europe)}
  max_damage_spain[class] = {structure, content, total} in EUR/m2 (2010 prices)
"""
import json

import _env  # noqa: F401
import numpy as np
import pandas as pd

x = pd.ExcelFile("data/raw/jrc/jrc_ddf.xlsx")
df = x.parse("Damage functions", header=None).iloc[3:, :]
cls, rows = None, {}
for _, r in df.iterrows():
    if isinstance(r[0], str) and r[0].strip():
        cls = r[0].strip().replace("\n", " ")
    if cls is None or not np.isfinite(pd.to_numeric(r[1], errors="coerce")):
        continue
    # columns: 2 = damage fraction EUROPE, 9 = standard deviation EUROPE (3 would be North America)
    rows.setdefault(cls, []).append((float(r[1]), pd.to_numeric(r[2], errors="coerce"), pd.to_numeric(r[9], errors="coerce")))
curves = {c: dict(depth_m=[a for a, _, _ in v], damage_fraction=[round(float(b), 4) for _, b, _ in v],
                  std=[None if not np.isfinite(s) else round(float(s), 4) for _, _, s in v]) for c, v in rows.items()}

maxd = {}
for sheet, key in (("MaxDamage-Residential", "Residential buildings"), ("MaxDamage-Commercial", "Commercial buildings"),
                   ("MaxDamage-Industrial", "Industrial buildings")):
    t = x.parse(sheet, header=None).iloc[3:, :4]
    t.columns = ["country", "structure", "content", "total"]
    s = t[t.country == "Spain"].iloc[0]
    maxd[key] = {k: round(float(s[k]), 1) for k in ("structure", "content", "total")}

json.dump(dict(curves=curves, max_damage_spain_eur_m2_2010=maxd,
               source="Huizinga, de Moel & Szewczyk (2017), Global flood depth-damage functions, JRC EUR 28552 EN, doi:10.2760/16510"),
          open("data/processed/jrc_curves.json", "w"), indent=1)
for c, v in curves.items():
    print(f"{c:32s}", v["damage_fraction"])
print("max damage Spain (EUR/m2, 2010):", maxd)
