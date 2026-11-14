import type { EChartsOption } from 'echarts'
import { useMemo } from 'react'
import type { SiteData } from '../data'
import { n0, n1, pct } from '../data'
import { FLOOD_BOUNDS, L } from '../layers'
import type { Palette } from '../theme'
import { LayerMap } from './LayerMap'
import { Card, Chart, DataTable, Info, Legend, Stat } from './ui'

export function FloodExtent({ data, palette, dark }: { data: SiteData; palette: Palette; dark: boolean }) {
  const s = data.summary
  const run = s.model.runs[s.final_run]
  const cal = run['Algemesi (AOI04)'], val = run['Horta Sud (AOI03)']
  const s1 = s.satellite.s1['20241101'].validation_vs_cems_vhr, s2 = s.satellite.s2['20241031'].vs_cems_vhr_clear_pixels_only
  const layers = useMemo(() => {
    const ls = [L.floodDepth(data.images.flood_depth), L.cemsObserved(palette), L.cemsFootprint(palette), L.s1(data.images.s1_flood), L.s2(data.images.s2_flood),
      L.basins(palette), L.streams(palette), L.municipalities(palette), ...L.gauges(palette).filter((g) => g.id === 'g-q')]
    ls.find((l) => l.id === 'g-q')!.defaultOn = false
    return ls
  }, [data.images, palette])

  const bars: EChartsOption = {
    grid: { left: 48, right: 16, top: 28, bottom: 40 },
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { color: palette['text-secondary'] } },
    xAxis: { type: 'category', data: ['Recall (share of the flood found)', 'Precision (share of the mapped area that is flood)'], axisLabel: { color: palette['text-muted'] } },
    yAxis: { type: 'value', max: 1, axisLabel: { color: palette['text-muted'], formatter: (v: number) => `${v * 100}%` }, splitLine: { lineStyle: { color: palette.grid } } },
    series: [
      { name: 'Sentinel-1 (1 Nov)', type: 'bar', data: [s1.recall, s1.precision], itemStyle: { color: palette['cat-2'] } },
      { name: 'Sentinel-2 (31 Oct, clear pixels)', type: 'bar', data: [s2.recall, s2.precision], itemStyle: { color: palette['cat-3'] } },
      { name: 'Model, Horta Sud (held out)', type: 'bar', data: [val.recall, val.precision], itemStyle: { color: palette['cat-1'] } },
    ],
  }
  const depthClass = run.area_km2_deeper_than as Record<string, number>
  const bv = s.building_validation as Record<string, { n: number; median_depth_m: number; share_modelled_flooded: number }>

  return (
    <div className="space-y-4">
      <Card title="Maximum flood extent and depth" subtitle="Modelled maximum depth at 30 m, with the independent Copernicus EMS outlines and the satellite detections as toggleable reference layers.">
        <div className="grid gap-3 md:grid-cols-4">
          <Stat label="Flooded area in model" value={`${n0(run.flooded_km2_in_grid)} km²`} sub={`depth ≥ ${run.flood_depth_threshold_m} m, clusters ≥ ${run.min_cluster_ha} ha`} />
          <Stat label="Horta Sud (held out): recall" value={pct(val.recall)} sub={`CSI ${val.csi} · precision ${pct(val.precision)}`} />
          <Stat label="Algemesí (calibration): recall" value={pct(cal.recall)} sub={`CSI ${cal.csi} · precision ${pct(cal.precision)}`} />
          <Stat label="Over-prediction (held out)" value={`${val.area_ratio_model_to_obs}×`} sub="modelled ÷ observed area in the CEMS footprint" />
        </div>
        <div className="mt-4"><LayerMap layers={layers} bounds={FLOOD_BOUNDS} dark={dark} height={640}
          attribution="SFINCS · FABDEM · Copernicus EMS EMSR773 · Contains modified Copernicus Sentinel data 2024" /></div>
        <Info>
          Turn on the CEMS outline (red) to compare. The model finds most of the observed flooding along the rivers, and floods too much of the flat ground in between:
          it has no drainage network, and at 90 m it cannot resolve streets. Treat depth under about 0.5 m as an upper bound.
        </Info>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="What each source contributes" subtitle="Share of the observed flood found, and share of mapped area that is real flood.">
          <Chart option={bars} height={300} label="Recall and precision for Sentinel-1, Sentinel-2 and the model" />
          <Legend palette={palette} items={[{ label: 'Sentinel-1', role: 'cat-2' }, { label: 'Sentinel-2', role: 'cat-3' }, { label: 'SFINCS model', role: 'cat-1' }]} />
          <Info>The model recovers far more of the flood than either satellite, but with many false alarms. The satellites have few false alarms where they see the flood, but see very little of it.</Info>
        </Card>
        <Card title="Area by depth" subtitle="Modelled flooded area deeper than each threshold.">
          <DataTable name="the numbers" caption="Flooded area by depth threshold" head={['Deeper than', 'Area km²']}
            rows={Object.entries(depthClass).map(([k, v]) => [`${k} m`, n1(v)])} />
          <div className="mt-3 space-y-1 text-sm text-ink-2">
            {Object.entries(depthClass).map(([k, v]) => (
              <div key={k} className="flex items-center gap-2"><span className="w-20 text-ink-3">&gt; {k} m</span>
                <span className="h-3 rounded-sm" style={{ width: `${(v / depthClass['0.3']) * 100}%`, background: palette['cat-1'] }} /><span className="tabular">{n1(v)} km²</span></div>))}
          </div>
        </Card>
      </div>

      <Card title="Independent check on buildings" subtitle="Beyond the flood outline: the emergency service's building damage grades. (River-gauge peaks are not yet compared: the model has no discharge output points.)">
        <h3 className="text-sm font-semibold text-ink">Building damage grades (CEMS photo-interpretation, Horta Sud)</h3>
        <p className="mt-1 max-w-4xl text-sm text-ink-2">
          CEMS graded individual buildings from very-high-resolution imagery. Modelled depth at those buildings should rise with the damage grade. It does.
        </p>
        <DataTable name="the grades" caption="Modelled depth at buildings by CEMS damage grade" head={['CEMS grade', 'Buildings', 'Median modelled depth m', 'Modelled as flooded']}
          rows={['Possibly damaged', 'Damaged', 'Destroyed'].filter((g) => bv[g]).map((g) => [g, n0(bv[g].n), bv[g].median_depth_m, pct(bv[g].share_modelled_flooded)])} />
        <Info>Only about half of the buildings CEMS graded as damaged fall in modelled flooding (the street-scale misses), but the ordering is right and every building graded destroyed is in deep modelled water.</Info>
      </Card>
    </div>
  )
}
