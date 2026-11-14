import type { EChartsOption } from 'echarts'
import { useMemo } from 'react'
import type { SiteData } from '../data'
import { n0, pct } from '../data'
import { FLOOD_BOUNDS, L } from '../layers'
import type { Palette } from '../theme'
import { LayerMap } from './LayerMap'
import { Card, Chart, DataTable, Info, Legend, Stat } from './ui'

const OCC_ORDER = ['residential', 'industrial', 'other', 'public', 'commercial', 'agricultural']

export function Exposure({ data, palette, dark }: { data: SiteData; palette: Palette; dark: boolean }) {
  const e = data.summary.exposure
  const layers = useMemo(() => [L.exposureGrid(), L.exposureResidential(), L.municipalities(palette), L.basins(palette, false), L.streams(palette, false)], [palette])
  const cov = e.overture_coverage
  const src = e.occupancy_source as Record<string, number>

  const occ = e.occupancy as Record<string, number>
  const opt: EChartsOption = {
    grid: { left: 96, right: 24, top: 8, bottom: 28 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', axisLabel: { color: palette['text-muted'] }, splitLine: { lineStyle: { color: palette.grid } } },
    yAxis: { type: 'category', inverse: true, data: OCC_ORDER, axisLabel: { color: palette['text-secondary'] } },
    series: [{ type: 'bar', data: OCC_ORDER.map((k) => occ[k] ?? 0), itemStyle: { color: palette['cat-1'] }, barMaxWidth: 18 }],
  }

  return (
    <div className="space-y-4">
      <Card title="Who and what was in the way" subtitle="Buildings from Overture Maps, people from WorldPop, shared onto the buildings.">
        <div className="grid gap-3 md:grid-cols-4">
          <Stat label="Buildings" value={n0(e.buildings)} sub={`${n0(e.floor_area_km2)} km² of floor area`} />
          <Stat label="People (WorldPop 2020)" value={n0(e.population)} sub="constrained, 100 m, shared onto buildings" />
          <Stat label="Residential" value={pct(occ.residential / e.buildings)} sub={`${n0(e.population_by_occ.residential)} people`} />
          <Stat label="Industrial" value={pct(occ.industrial / e.buildings)} sub="warehouses and estates along the rivers" />
        </div>
        <div className="mt-4"><LayerMap layers={layers} bounds={FLOOD_BOUNDS} dark={dark} height={600}
          attribution="Buildings © Overture Maps Foundation · Population: WorldPop (CC BY 4.0)" /></div>
        <Info>Click a cell for its people, buildings, residential share and mean number of floors. Switch to the residential share layer to see the industrial estates (orange) among the housing.</Info>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="What the building data does and does not say" subtitle="Share of buildings with each attribute, and how the gaps are filled.">
          <DataTable name="the coverage" caption="Overture attribute coverage" head={['Attribute', 'Coverage', 'Used for', 'Gap handling']} rows={[
            ['Use (subtype / class)', pct(cov.subtype_or_class), 'Depth–damage curve and value', 'Neighbour majority for residential or industrial blocks; else footprint area'],
            ['Number of floors', pct(cov.num_floors), 'Floor area, storeys reached by water, people', 'Median by use'],
            ['Facade material', pct(cov.facade_material, 2), 'Not usable', 'Curves are by use, not by material'],
            ['Roof material', pct(cov.roof_material, 2), 'Not usable', '–'],
          ]} />
          <Info>
            The brief asked for occupancy and construction material as attributes. Occupancy exists for only {pct(cov.subtype_or_class)} of buildings and material for essentially none,
            so use is inferred ({n0(src.neighbour)} buildings from labelled neighbours, {n0(src.rule)} by footprint area) and the vulnerability curves are by use. This is the largest
            uncertainty in the damage step. The Spanish cadastre (use and floors per building) would be the better source.
          </Info>
        </Card>
        <Card title="Buildings by use" subtitle="After filling the gaps; only labelled buildings can be public or commercial.">
          <Chart option={opt} height={260} label="Number of buildings by inferred use" />
          <Legend palette={palette} items={[{ label: 'Buildings', role: 'cat-1' }]} />
          <Info>
            Public and commercial buildings are under-counted: only buildings explicitly labelled as such are placed there. Mixed-use ground floors in the dense towns are treated as residential.
            People are shared among a 100 m cell's buildings in proportion to floor area (residential buildings first), so cell totals match WorldPop exactly; the split between neighbouring buildings is an estimate.
          </Info>
        </Card>
      </div>
    </div>
  )
}
