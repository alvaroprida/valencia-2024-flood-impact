import type { SiteData } from '../data'
import type { TabKey } from '../App'
import { Card, Info, Ref, Steps } from './ui'

const SOURCES: { name: string; kind: string; spec: string; why: string; limit: string }[] = [
  { name: 'Sentinel-1 SAR (C-band)', kind: 'Radar, open', spec: '10 m · 6 days (one orbit ≈ 12)',
    why: 'Sees through cloud and at night, which matters in a storm. Open water is dark in the image, so change against a dry baseline maps flooding. The workhorse of flood mapping.',
    limit: 'No pass between 26 Oct and 1 Nov: the first post-event scene is ~3 days after the peak, when the flash flood had drained. Flooded streets and orchards are not dark.' },
  { name: 'Sentinel-2 (optical)', kind: 'Optical, open', spec: '10–20 m · 5 days',
    why: 'Clear-sky water index (MNDWI) separates water from land well, including turbid flood water, and shows what the radar cannot: flooded vegetation and bare ground.',
    limit: 'Cloud. On 31 Oct, the closest scene, only about half of the Horta Sud validation area was visible.' },
  { name: 'Landsat 8 / 9', kind: 'Optical, open', spec: '30 m · 8 days',
    why: 'An extra optical pass (30 Oct, the day after the peak), useful when Sentinel-2 misses a date.',
    limit: 'Cloud-covered over the study area on 30 Oct (about 1 % clear).' },
  { name: 'Very-high-resolution optical and radar', kind: 'Commercial, used by Copernicus EMS', spec: '0.3–3 m · tasked',
    why: 'WorldView, GeoEye, Pléiades, COSMO-SkyMed, ICEYE, TerraSAR-X: what the emergency service actually used (31 Oct to 8 Nov). Photo-interpreted flood outlines and mud lines.',
    limit: 'Not open. Here it is the independent reference only: nothing in the model is tuned on Horta Sud.' },
  { name: 'FABDEM terrain (30 m)', kind: 'Open', spec: 'static',
    why: 'Terrain with forests and buildings removed: tells water where to go, and turns a water level into a depth.',
    limit: '30 m cannot resolve streets, levees, culverts or the Albufera outlets.' },
  { name: 'Rain and river gauges (SAIH, AEMET)', kind: 'Open', spec: '5 min to daily',
    why: 'Ground truth for the rain that fell (up to 770 mm in a day) and the flows that resulted. Satellite rainfall and reanalysis miss most of it.',
    limit: 'Sparse in the headwaters, some sensors failed in the flood, and hourly series are not yet available (totals only).' },
  { name: 'SFINCS hydrodynamic model', kind: 'Open', spec: '90 m grid, 45 m subgrid',
    why: 'Fills in what no sensor saw: the maximum extent and depth, from the rainfall and the terrain. Rain-on-grid, as used in the Madagascar study.',
    limit: 'No drainage network, culverts, dams or street detail; roughness and infiltration are uncertain, so it is calibrated.' },
]

export function Approach({ go }: { data: SiteData; go: (k: TabKey) => void }) {
  return (
    <div className="space-y-4">
      <Card title="The problem" subtitle="A flash flood is over before most satellites arrive.">
        <p className="max-w-4xl text-sm leading-relaxed text-ink-2">
          On 29 October 2024 up to 771 mm of rain fell in about 14 hours in the hills behind Valencia. The Rambla del Poyo and the
          Magro rose within hours and drained within a day. Emergency responders needed to know, within 24–72 hours, which areas
          were flooded, how deep, and how many people and buildings were affected. No single sensor gives that for a flash flood:
          each sees part of it, late. This case study shows what each open source contributes, where it fails (with numbers), and how they are combined.
        </p>
      </Card>

      <Card title="Sources, and why each is relevant" subtitle="What each one is good for, and what limited it in this event.">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-sm">
            <thead>
              <tr className="border-b border-line text-left text-ink-3">
                <th className="py-1.5 pr-3 font-medium">Source</th><th className="py-1.5 pr-3 font-medium">Type · resolution</th>
                <th className="py-1.5 pr-3 font-medium">Why it is relevant</th><th className="py-1.5 font-medium">Limits in this event</th>
              </tr>
            </thead>
            <tbody>
              {SOURCES.map((s) => (
                <tr key={s.name} className="border-b border-line align-top last:border-0">
                  <td className="py-2 pr-3 font-medium text-ink">{s.name}</td>
                  <td className="py-2 pr-3 text-ink-2">{s.kind}<br /><span className="text-ink-3">{s.spec}</span></td>
                  <td className="py-2 pr-3 text-ink-2">{s.why}</td>
                  <td className="py-2 text-ink-2">{s.limit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="How they are combined" subtitle="Each step is a tab; every step reports how it scores against the independent reference.">
        <Steps items={[
          { title: 'Look at what open satellites can see', body: <>Sentinel-1 radar change detection and Sentinel-2 water index, scored against Copernicus EMS. This is where the limits show. <Ref to="satellite">See the evidence</Ref>.</> },
          { title: 'Reconstruct the rain that fell', body: <>Station totals from SAIH and AEMET interpolated, shaped in time by ERA5, cross-validated by leaving each gauge out. <Ref to="rainfall">See the rainfall</Ref>.</> },
          { title: 'Model the flood', body: <>SFINCS rain-on-grid driven by that rainfall, with infiltration and roughness calibrated on one area and tested on another. <Ref to="model">See the model</Ref>.</> },
          { title: 'Check against what is independent', body: <>Flood outlines from very-high-resolution imagery and the emergency service's building damage grades. (River-gauge hydrographs are not yet used: see Method &amp; sources.) <Ref to="extent">See extent and depth</Ref>.</> },
          { title: 'Turn depth into impact and priority', body: <>Buildings and people from Overture and WorldPop, damage from JRC depth–damage curves, then a transparent ranking of where to act first. <button type="button" className="font-medium text-accent underline decoration-dotted underline-offset-2" onClick={() => go('exposure')}>Exposure</button> → Vulnerability → Impact → Prioritisation.</> },
        ]} />
        <Info>
          <b>No circularity.</b> The Copernicus EMS flood outlines are used only to score results. Calibration uses Algemesí
          (CEMS AOI04); Horta Sud (AOI03) is held out and reported as it comes. Satellite detections are never fed into the model.
        </Info>
      </Card>
    </div>
  )
}
