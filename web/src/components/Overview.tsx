import { useMemo } from 'react'
import type { TabKey } from '../App'
import type { SiteData } from '../data'
import { n0, pct } from '../data'
import { FLOOD_BOUNDS, L } from '../layers'
import type { Palette } from '../theme'
import { LayerMap } from './LayerMap'
import { Card, Stat } from './ui'

export function Overview({ data, go, palette, dark }: { data: SiteData; go: (k: TabKey) => void; palette: Palette; dark: boolean }) {
  const s = data.summary
  const run = s.model.runs[s.final_run]
  const val = run['Horta Sud (AOI03)']
  const im = s.impact
  const s1 = s.satellite.s1['20241101'].validation_vs_cems_vhr
  const layers = useMemo(() => {
    const ls = [L.floodDepth(data.images.flood_depth), L.buildings(), L.basins(palette), L.streams(palette), ...L.gauges(palette).filter((g) => g.id === 'g-q' || g.id === 'g-rain')]
    ls.find((l) => l.id === 'bld')!.defaultOn = false
    ls.forEach((l) => { if (l.id.startsWith('g-')) l.defaultOn = false })
    return ls
  }, [data.images, palette])

  const CARDS: [TabKey, string, string][] = [
    ['approach', 'Hazard · Approach', 'Which sources, why each is relevant, and how they are combined.'],
    ['satellite', 'Hazard · Satellite evidence', `Radar and optical, scored against Copernicus EMS: they found ${pct(s1.recall, 1)} of the flood.`],
    ['rainfall', 'Hazard · Rainfall & gauges', 'Rain and river gauges on the map; hourly rainfall from station totals.'],
    ['model', 'Hazard · Flood model', 'SFINCS rain-on-grid, calibrated on Algemesí, tested on Horta Sud.'],
    ['extent', 'Hazard · Flood extent & depth', 'The maximum depth layer, with every reference toggleable.'],
    ['exposure', 'Exposure', 'Buildings and people, with what the data does and does not say.'],
    ['vulnerability', 'Vulnerability', 'Depth–damage curves and a one-building calculator.'],
    ['impact', 'Impact', 'Buildings coloured by damage, people, losses, cut roads, facilities.'],
    ['priority', 'Prioritisation', 'A ranking of where to act first, with adjustable weights.'],
  ]

  return (
    <div className="space-y-4">
      <Card title="Overview" subtitle="29 October 2024: up to 771 mm of rain in about 14 hours in the hills behind Valencia; the Rambla del Poyo and the Magro flooded the Horta Sud and the Ribera within hours.">
        <div className="grid gap-3 md:grid-cols-4">
          <Stat hero label="Buildings flooded (modelled)" value={n0(im.buildings_flooded)} sub={`${n0(im.people_in_flooded_buildings)} people in them`} />
          <Stat label="Flood found by radar, 1 Nov" value={pct(s1.recall, 1)} sub="Sentinel-1, vs Copernicus EMS" />
          <Stat label="Flood found by the model" value={pct(val.recall)} sub={`Horta Sud, held out · over-predicts ${val.area_ratio_model_to_obs}×`} />
          <Stat label="Building loss, modelled" value={`${n0(im.loss_eur_2010 / 1e6)} M€`} sub="2010 prices" />
        </div>
        <div className="mt-4"><LayerMap layers={layers} bounds={FLOOD_BOUNDS} dark={dark} height={560}
          attribution="SFINCS · Overture Maps · Copernicus EMS EMSR773" /></div>
      </Card>

      <Card title="What this case study shows">
        <ol className="max-w-4xl list-decimal space-y-2 pl-5 text-sm leading-relaxed text-ink-2">
          <li><b className="text-ink">Open satellites cannot see a flash flood in time.</b> Sentinel-1 found {pct(s1.recall, 1)} of it (first pass three days after the peak, water gone, urban and orchard flooding invisible); Sentinel-2 was under cloud where it mattered; Landsat was cloud-covered.</li>
          <li><b className="text-ink">Station rainfall plus a hydrodynamic model fill the gap.</b> Gauges set the amounts, ERA5 the timing, SFINCS the water. It finds {pct(val.recall)} of the flood Copernicus EMS mapped in Horta Sud, an area it was not tuned on, but floods about {val.area_ratio_model_to_obs}× too much area.</li>
          <li><b className="text-ink">Depth becomes impact.</b> Overture buildings, WorldPop people and JRC curves turn depth into damage; the share of buildings modelled as flooded rises with the emergency service's own damage grades, and all those graded destroyed sit in deep water.</li>
          <li><b className="text-ink">Impact becomes a priority.</b> Cells are ranked by severity-weighted people, loss, flooded critical facilities and cut roads, with adjustable weights and a stability test.</li>
        </ol>
      </Card>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {CARDS.map(([k, title, text]) => (
          <button key={k} type="button" onClick={() => go(k)} className="rounded-xl border border-line bg-surface p-4 text-left hover:border-accent">
            <div className="text-sm font-semibold text-ink">{title}</div>
            <div className="mt-1 text-sm leading-relaxed text-ink-2">{text}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
