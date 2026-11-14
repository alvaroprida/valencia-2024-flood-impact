import type { SiteData } from '../data'
import { Card } from './ui'

const SOURCES: [string, string, string][] = [
  ['Copernicus Sentinel-1 RTC, Sentinel-2 L2A, Landsat 8/9', 'Satellite detection (radar, optical)', 'Copernicus open licence; USGS public domain. Via Microsoft Planetary Computer.'],
  ['Copernicus EMS EMSR773 (flood delineation and grading products)', 'Independent reference (flood outlines, depth classes, building damage grades)', 'Copernicus EMS, free and open'],
  ['FABDEM V1-2', 'Terrain for the model and for depth', 'CC BY-NC-SA 4.0, non-commercial'],
  ['Copernicus DEM GLO-30', 'Slope and height-above-drainage masks for the satellite step', 'Copernicus open licence'],
  ['ESA WorldCover 2021', 'Manning roughness and curve number', 'CC BY 4.0'],
  ['SAIH Júcar (CHJ) event report, 15 Jan 2025', 'Rain gauge totals, river peaks, basin rainfall', 'Public report'],
  ['SAIH station layers (MITECO, 2014)', 'Station coordinates', '© Ministerio para la Transición Ecológica y el Reto Demográfico, free use with attribution'],
  ['AEMET OpenData', 'Station rainfall (daily)', 'AEMET, CC BY 4.0'],
  ['ERA5 via Open-Meteo', 'Hourly rainfall timing', 'Copernicus / ECMWF; Open-Meteo CC BY 4.0'],
  ['Overture Maps (buildings, divisions, places, transportation)', 'Exposure, municipalities, critical facilities, roads', 'ODbL (buildings, divisions, transportation); CDLA Permissive 2.0 (places)'],
  ['WorldPop 2020, constrained, 100 m', 'Population', 'CC BY 4.0'],
  ['JRC global flood depth–damage functions (Huizinga et al. 2017)', 'Vulnerability curves and maximum damage values', 'JRC, EUR 28552 EN'],
  ['SFINCS v2.4.1 (Deltares)', 'Hydrodynamic model', 'Open source; run from the public Docker image'],
  ['Basemap © OpenStreetMap contributors, OpenFreeMap', 'Map background', 'ODbL'],
]

const REFS = [
  'Copernicus Emergency Management Service (2024). EMSR773: Flood in Valencia Region, Spain. rapidmapping.emergency.copernicus.eu/EMSR773',
  'Confederación Hidrográfica del Júcar (2025). Episodio de lluvias y avenidas del 28 de octubre al 4 de noviembre de 2024. saih.chj.es',
  'AEMET (2024). Informe del episodio de la DANA del 29 de octubre de 2024.',
  'Huizinga, J., de Moel, H. & Szewczyk, W. (2017). Global flood depth-damage functions. JRC Technical Report EUR 28552 EN, doi:10.2760/16510.',
  'Hawker, L. et al. (2022). A 30 m global map of elevation with forests and buildings removed. Environmental Research Letters 17, 024016.',
  'Leijnse, T. et al. (2021). Modeling compound flooding in coastal systems using a computationally efficient reduced-physics solver. Coastal Engineering 163, 103796.',
  'Zanaga, D. et al. (2022). ESA WorldCover 10 m 2021 v200. doi:10.5281/zenodo.7254221.',
  'Hersbach, H. et al. (2020). The ERA5 global reanalysis. Q. J. R. Meteorol. Soc. 146, 1999–2049.',
]

export function Method({ data }: { data: SiteData }) {
  void data
  return (
    <div className="space-y-4">
      <Card title="Data and licences" subtitle="Figures and layers derive from these sources and follow their licences.">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead><tr className="border-b border-line text-left text-ink-3"><th className="py-1.5 pr-4 font-medium">Source</th><th className="py-1.5 pr-4 font-medium">Used for</th><th className="py-1.5 font-medium">Licence</th></tr></thead>
            <tbody>{SOURCES.map((s) => (
              <tr key={s[0]} className="border-b border-line align-top last:border-0"><td className="py-1.5 pr-4 text-ink">{s[0]}</td><td className="py-1.5 pr-4 text-ink-2">{s[1]}</td><td className="py-1.5 text-ink-2">{s[2]}</td></tr>))}</tbody>
          </table>
        </div>
        <p className="mt-3 text-sm text-ink-2">FABDEM is non-commercial, so the flood layers derived from it are for research and demonstration only. AVAMET data was not used: its licence (CC BY-NC-ND) forbids derivatives.</p>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Assumptions that move the results">
          <ul className="space-y-2 text-sm leading-relaxed text-ink-2">
            <li><b className="text-ink">Rainfall.</b> Gauge totals interpolated by inverse-distance weighting, split in time with ERA5. 95 % of the SAIH episode total is assumed to fall in the model window. The two wettest SAIH gauges (Chiva, Real) have approximate positions.</li>
            <li><b className="text-ink">Infiltration.</b> Curve numbers from a literature lookup, one hydrologic soil group for the whole domain. It is a calibration parameter, not a measurement.</li>
            <li><b className="text-ink">Flooded means</b> depth ≥ 0.3 m in clusters ≥ 1 ha. The threshold was chosen from a sweep on the base run, then fixed for all runs.</li>
            <li><b className="text-ink">Albufera</b> held at sea level in the model; sea at +0.3 m.</li>
            <li><b className="text-ink">Buildings.</b> Use is inferred for ~80 % of buildings; floors for ~26 % are the median by use; no construction material.</li>
            <li><b className="text-ink">Population.</b> WorldPop 2020 (not 2024), shared onto buildings by floor area. Ground-level exposure = people ÷ storeys.</li>
            <li><b className="text-ink">Losses</b> in 2010 euros, JRC Europe curves; not a claims estimate.</li>
          </ul>
        </Card>
        <Card title="What would make it better">
          <ul className="space-y-2 text-sm leading-relaxed text-ink-2">
            <li><b className="text-ink">SAIH 5-minute rainfall and flow series</b> in place of ERA5 timing, and exact positions for all gauges.</li>
            <li><b className="text-ink">A 5 m national terrain model</b> (IGN MDT05) and a drainage and culvert network for the Horta Sud streets, with 20–30 m cells.</li>
            <li><b className="text-ink">The Spanish cadastre</b> for building use and floors, in place of inferred use.</li>
            <li><b className="text-ink">River-gauge hydrographs.</b> Add discharge output lines to the model and compare with the CHJ peaks (Poyo 2,283 m³/s, Júcar at Algemesí 1,523 m³/s). Not done here.</li>
            <li><b className="text-ink">Dam operations</b> (Forata, Loriguilla, Benagéber) and the Turia diversion, which the model ignores.</li>
            <li><b className="text-ink">Data assimilation:</b> use the partial satellite and gauge observations to correct the model in real time, not only to score it.</li>
          </ul>
        </Card>
      </div>

      <Card title="Reproducibility">
        <p className="max-w-4xl text-sm leading-relaxed text-ink-2">
          The full pipeline, from scene search to this site, is in the repository: <a className="text-accent underline underline-offset-2" href="https://github.com/alvaroprida/valencia-2024-flood-impact">github.com/alvaroprida/valencia-2024-flood-impact</a>.
          Python scripts <code>pipeline/00…28</code> run in order from the repository root; raw and processed data are not committed. SFINCS runs from the public{' '}
          <code>deltares/sfincs-cpu</code> image, here unpacked into a WSL1 distribution because virtualisation was unavailable.
        </p>
      </Card>

      <Card title="References">
        <ul className="space-y-1.5 text-sm leading-relaxed text-ink-2">{REFS.map((r) => <li key={r}>{r}</li>)}</ul>
      </Card>
    </div>
  )
}
