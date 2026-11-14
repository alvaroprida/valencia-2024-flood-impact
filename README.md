# Valencia 2024 · Rapid flood impact mapping

Case study of the 29 October 2024 DANA flash floods in Valencia (Horta Sud, Poyo, Magro, lower Turia):
how much of a flash flood can be reconstructed from open satellite data, and how to fuse partial
observations, rainfall and river gauges, and a hydrodynamic model into a maximum flood extent and
depth layer, then into building and population impact and a response priority ranking.

> **Work in progress.** Not an official hazard or damage map.

## Findings so far

| Source | Date | Result vs Copernicus EMS very-high-resolution flood outlines |
|---|---|---|
| Sentinel-1 SAR change detection | 1 and 6 Nov | Recall under 1%: water had drained before the first usable pass; false alarms in the Albufera rice paddies |
| Sentinel-2 MNDWI | 31 Oct | Only 53% of the validated area is cloud-free; recall 8% on clear pixels |
| Landsat 8 | 30 Oct | 99% cloud over the study area |

Open optical and radar imagery each see only part of this flood, so the maximum extent and depth are
reconstructed with a hydrodynamic model (SFINCS) forced by station rainfall, constrained by the partial
observations and scored against Copernicus EMS activation EMSR773.

## Plan

Overview, Hazard, Exposure, Vulnerability, Impact, Prioritisation, with toggleable map layers (basins,
rivers, river and rain gauges, flood extent and depth, buildings, population).

## Pipeline

Python in [`pipeline/`](pipeline); run from the repository root.

| Script | Purpose |
|---|---|
| `00_search_scenes.py` | Sentinel-1 / Sentinel-2 scene availability around the event |
| `01_inspect_cems.py` | Attributes of the downloaded EMSR773 layers |
| `02_fetch_s1.py`, `03_fetch_dem.py` | Sentinel-1 RTC and Copernicus DEM onto a 10 m grid, slope, HAND |
| `04_sar_flood.py` | SAR change detection and validation |
| `05_optical.py`, `06_optical_flood.py` | Sentinel-2 / Landsat water index and validation |
| `07_inspect_buildings.py` | Overture building attributes |

Raw and processed data are not committed (`data/` is ignored).

## Data

Copernicus Sentinel-1/2 and Copernicus DEM (via Microsoft Planetary Computer), Copernicus EMS EMSR773,
Overture Maps buildings, WorldPop 2020 (constrained), AEMET and SAIH Júcar station data (planned).
Follow each source's licence.
