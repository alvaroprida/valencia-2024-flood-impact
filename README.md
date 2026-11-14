# Valencia 2024 · Rapid flood impact mapping

**[▶ Open the site](https://alvaroprida.github.io/valencia-2024-flood-impact/)**

Case study of the 29 October 2024 DANA flash floods in Valencia (Rambla del Poyo, Magro, Horta Sud, Ribera):
what open satellite data can and cannot see of a flash flood, and how imagery, station rainfall and a
hydrodynamic model (SFINCS) are combined into a flood extent and depth layer, then into building and
population impact (Overture, WorldPop, JRC depth–damage curves) and a ranking of where to act first.
Validated against Copernicus EMS activation EMSR773.

> **Research case study, not an official hazard, damage or response map.** The site shows how every step
> scores against the independent reference, including where it fails.

## What the site shows

| Tab | Content |
|---|---|
| **Overview** | Headline numbers and what the case study shows |
| **Hazard → Approach & sources** | Which sources, why each is relevant, how they are combined |
| **Hazard → Satellite evidence** | Sentinel-1 / Sentinel-2 flood detection scored against Copernicus EMS; why they fail for a flash flood |
| **Hazard → Rainfall & gauges** | Rain and river gauges on the map; hourly rainfall from station totals (ERA5 for timing), cross-validated |
| **Hazard → Flood model** | SFINCS rain-on-grid setup, calibration on Algemesí, held-out test on Horta Sud |
| **Hazard → Flood extent & depth** | Modelled maximum depth with CEMS and satellite layers toggleable; building damage-grade check |
| **Exposure** | Buildings and population, with data coverage and gap handling |
| **Vulnerability** | JRC Europe depth–damage curves and a one-building calculator |
| **Impact** | Flooded buildings coloured by damage, people, losses, roads cut, critical facilities |
| **Prioritisation** | 250 m cells ranked by an adjustable score; stability under random weights |
| **Method & sources** | Licences, assumptions, limitations, references |

## How it is built

The pipeline is Python in [`pipeline/`](pipeline), run from the repository root; it writes web layers to
[`web/public/data/`](web/public/data). The site is a static React + TypeScript app (Vite, Tailwind, ECharts,
MapLibre), deployed to GitHub Pages by [`deploy-pages.yml`](.github/workflows/deploy-pages.yml).

| Script | Purpose |
|---|---|
| `00`–`07` | Scene search, Copernicus EMS reference, Sentinel-1 / Sentinel-2 / Landsat detection and validation |
| `08`, `11`–`14` | AEMET stations, CHJ event report parsing, MITECO SAIH station layers, merged gauge layer |
| `10`, `16` | FABDEM terrain, catchments and stream network |
| `15`, `17` | ERA5 hourly timing; gauge-interpolated hourly rainfall field with leave-one-out test |
| `18`, `19`, `25`, `26` | Land cover → roughness and curve number, SFINCS model builder, Albufera lake, calibration variants |
| `09`, `tools/` | SFINCS image pull from Docker Hub and run under WSL1 (no Docker Desktop) |
| `20`, `21`, `23` | Exposure (buildings, people), JRC depth–damage curves, impact |
| `22` | SFINCS output → 30 m flood depth, scoring against CEMS |
| `24` | Prioritisation |
| `27`, `28` | Export web layers and the summary JSON |

```bash
cd web
npm ci
npm run dev       # local preview
npm run build     # static build in web/dist
```

Raw and processed data, models and the Python environment are not committed.

## Data and licences

Copernicus Sentinel-1/2, Landsat, Copernicus DEM and ESA WorldCover (via Microsoft Planetary Computer),
Copernicus EMS EMSR773, FABDEM (CC BY-NC-SA 4.0, **non-commercial**), SAIH Júcar (CHJ) report, MITECO SAIH
station layers, AEMET OpenData, ERA5 via Open-Meteo, Overture Maps (ODbL / CDLA), WorldPop (CC BY 4.0), JRC
depth–damage functions. Full list and references on the *Method & sources* tab.
AVAMET data was not used: its licence (CC BY-NC-ND) forbids derivatives.

Site code: MIT licence. Data and figures follow the licences of their sources.
