import type { EChartsOption } from 'echarts'
import { useMemo } from 'react'
import type { SiteData } from '../data'
import { n0, pct } from '../data'
import { FLOOD_BOUNDS, L } from '../layers'
import type { Palette } from '../theme'
import { DAMAGE_RAMP } from '../theme'
import { LayerMap } from './LayerMap'
import { Card, Chart, DataTable, Info, Stat } from './ui'

export function Impact({ data, palette, dark }: { data: SiteData; palette: Palette; dark: boolean }) {
  const im = data.summary.impact
  const layers = useMemo(() => {
    const ls = [L.buildings(), L.floodDepth(data.images.flood_depth), L.impactMunicipalities(), L.roadsCut(palette), L.facilities(), L.cemsDamage(palette),
      L.municipalities(palette), L.streams(palette, false)]
    ls.find((l) => l.id === 'flood-depth')!.defaultOn = false
    return ls
  }, [data.images, palette])

  const cls = im.by_damage_class as Record<string, number>
  const order = ['minor', 'moderate', 'major', 'severe']
  const clsOpt: EChartsOption = {
    grid: { left: 70, right: 16, top: 8, bottom: 28 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', axisLabel: { color: palette['text-muted'] }, splitLine: { lineStyle: { color: palette.grid } } },
    yAxis: { type: 'category', inverse: true, data: order.map((k) => k[0].toUpperCase() + k.slice(1)), axisLabel: { color: palette['text-secondary'] } },
    series: [{ type: 'bar', barMaxWidth: 20, data: order.map((k, i) => ({ value: cls[k] ?? 0, itemStyle: { color: DAMAGE_RAMP[i].color } })) }],
  }
  const occ = im.by_occupancy as Record<string, { flooded: number; loss_meur: number }>
  const occKeys = Object.keys(occ).filter((k) => occ[k].loss_meur > 0).sort((a, b) => occ[b].loss_meur - occ[a].loss_meur)
  const occOpt: EChartsOption = {
    grid: { left: 96, right: 16, top: 8, bottom: 28 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v) => `${Math.round(Number(v))} M€` },
    xAxis: { type: 'value', name: 'M€ (2010 prices)', axisLabel: { color: palette['text-muted'] }, splitLine: { lineStyle: { color: palette.grid } } },
    yAxis: { type: 'category', inverse: true, data: occKeys, axisLabel: { color: palette['text-secondary'] } },
    series: [{ type: 'bar', barMaxWidth: 20, data: occKeys.map((k) => occ[k].loss_meur), itemStyle: { color: palette['cat-2'] } }],
  }
  const mun = im.top_municipalities_by_people as { municipality: string; buildings: number; people: number; people_ground: number; loss_meur: number; mean_depth: number; share_buildings: number }[]
  const munOpt: EChartsOption = {
    grid: { left: 110, right: 16, top: 8, bottom: 28 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', axisLabel: { color: palette['text-muted'] }, splitLine: { lineStyle: { color: palette.grid } } },
    yAxis: { type: 'category', inverse: true, data: mun.slice(0, 12).map((m) => m.municipality), axisLabel: { color: palette['text-secondary'] } },
    series: [{ type: 'bar', barMaxWidth: 16, data: mun.slice(0, 12).map((m) => Math.round(m.people_ground)), itemStyle: { color: palette['cat-1'] } }],
  }

  return (
    <div className="space-y-4">
      <Card title="Buildings, people and losses in the flood" subtitle="Every flooded building coloured by modelled damage ratio. Zoom in; click a building, a municipality, a road or a facility.">
        <div className="grid gap-3 md:grid-cols-4">
          <Stat label="Buildings flooded" value={n0(im.buildings_flooded)} sub={`of ${n0(im.buildings_total)} (${pct(im.buildings_flooded / im.buildings_total)})`} />
          <Stat label="People in flooded buildings" value={n0(im.people_in_flooded_buildings)} sub={`${n0(im.people_ground_exposed)} at ground level · ${n0(im.people_in_buildings_over_1m)} where > 1 m`} />
          <Stat label="Building loss" value={`${n0(im.loss_eur_2010 / 1e6)} M€`} sub="2010 prices, structure + content" />
          <Stat label="Roads under water" value={`${n0(im.road_km_flooded_over_30cm)} km`} sub={`${im.facilities_flooded.school} schools · ${im.facilities_flooded.hospital} health centres flooded`} />
        </div>
        <div className="mt-4"><LayerMap layers={layers} bounds={FLOOD_BOUNDS} dark={dark} height={680}
          attribution="SFINCS · Overture Maps · WorldPop · JRC depth–damage functions · Copernicus EMS EMSR773" /></div>
        <Info>
          Switch on <b>CEMS building damage grades</b> to compare with the emergency service's photo-interpretation: where it graded buildings destroyed (dark), the model has deep water.
          Counts and losses are for the modelled flood, which over-predicts area (see Flood extent): read them as an upper estimate, strongest in the shallow ranges.
        </Info>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Damage classes" subtitle="Share of value lost, number of buildings.">
          <Chart option={clsOpt} height={200} label="Number of buildings per damage class" />
          <Info>Minor &lt; 10 %, moderate 10–30 %, major 30–60 %, severe &gt; 60 %.</Info>
        </Card>
        <Card title="Loss by use" subtitle="Million euros, 2010 prices.">
          <Chart option={occOpt} height={200} label="Building loss by use" />
          <Info>Industrial and residential dominate: a few large industrial buildings carry high value per building.</Info>
        </Card>
        <Card title="People by municipality" subtitle="Ground-level exposure: people ÷ storeys, in flooded buildings.">
          <Chart option={munOpt} height={200} label="People exposed at ground level by municipality" />
        </Card>
      </div>

      <Card title="Municipalities" subtitle="Ranked by people in flooded buildings.">
        <DataTable name="the table" caption="Impact by municipality" head={['Municipality', 'Flooded buildings', '% of buildings', 'People in flooded buildings', 'Ground level', 'Mean depth m', 'Loss M€']}
          rows={mun.map((m) => [m.municipality, n0(m.buildings), pct(m.share_buildings), n0(m.people), n0(m.people_ground), m.mean_depth.toFixed(1), n0(m.loss_meur)])} />
        <Info>
          People in flooded buildings counts everyone registered to a building with water in it; the ground-level figure divides by the number of storeys and is closer to those in immediate danger.
          Numbers are model estimates, not casualty or damage counts.
        </Info>
      </Card>
    </div>
  )
}
