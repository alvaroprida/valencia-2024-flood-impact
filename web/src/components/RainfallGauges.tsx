import type { EChartsOption } from 'echarts'
import { useMemo } from 'react'
import type { SiteData } from '../data'
import { n0 } from '../data'
import { L, STUDY_BOUNDS } from '../layers'
import type { Palette } from '../theme'
import { LayerMap } from './LayerMap'
import { Card, Chart, DataTable, Info, Legend, Stat } from './ui'

const SLOTS = ['cat-1', 'cat-2', 'cat-3', 'cat-4'] as const

export function RainfallGauges({ data, palette, dark }: { data: SiteData; palette: Palette; dark: boolean }) {
  const rf = data.summary.rainfall
  const layers = useMemo(() => [L.rainTotal(data.images.rain_total), ...L.gauges(palette), L.basins(palette), L.streams(palette, false), L.albufera(palette)],
    [data.images, palette])

  const hy = rf.hyetograph_utc
  const names = Object.keys(hy.values) as string[]
  const t0 = Date.parse(hy.start)
  const hours = hy.values[names[0]].map((_: number, i: number) => new Date(t0 + i * 3600e3))
  const label = (d: Date) => `${d.getUTCDate()} Oct ${String(d.getUTCHours()).padStart(2, '0')}h`

  const hyOpt: EChartsOption = {
    grid: { left: 48, right: 16, top: 24, bottom: 56 },
    tooltip: { trigger: 'axis', valueFormatter: (v) => `${Number(v).toFixed(1)} mm/h` },
    xAxis: { type: 'category', data: hours.map(label), axisLabel: { color: palette['text-muted'], interval: 5 }, axisLine: { lineStyle: { color: palette.axis } } },
    yAxis: { type: 'value', name: 'mm/h, catchment mean', nameTextStyle: { color: palette['text-muted'] }, axisLabel: { color: palette['text-muted'] }, splitLine: { lineStyle: { color: palette.grid } } },
    series: names.map((n, i) => ({ name: n, type: 'line', showSymbol: false, data: hy.values[n], lineStyle: { width: 2, color: palette[SLOTS[i % 4]] }, itemStyle: { color: palette[SLOTS[i % 4]] } })),
  }

  const sc: [number, number, string, string][] = rf.scatter
  const mx = Math.max(...sc.map((s) => Math.max(s[0], s[1]))) * 1.05
  const scOpt: EChartsOption = {
    grid: { left: 56, right: 16, top: 16, bottom: 48 },
    tooltip: { formatter: (p: unknown) => { const d = (p as { data: [number, number, string, string] }).data; return `${d[2]} (${d[3]})<br/>gauge ${n0(d[0])} mm · left-out estimate ${n0(d[1])} mm` } },
    xAxis: { type: 'value', name: 'gauge total (mm)', nameLocation: 'middle', nameGap: 28, min: 0, max: mx, axisLabel: { color: palette['text-muted'] }, splitLine: { lineStyle: { color: palette.grid } } },
    yAxis: { type: 'value', name: 'estimate without that gauge (mm)', min: 0, max: mx, axisLabel: { color: palette['text-muted'] }, nameTextStyle: { color: palette['text-muted'] }, splitLine: { lineStyle: { color: palette.grid } } },
    series: [
      { type: 'line', data: [[0, 0], [mx, mx]], showSymbol: false, lineStyle: { color: palette.neutral, type: 'dashed', width: 1 }, silent: true },
      { type: 'scatter', symbolSize: 8, data: sc, itemStyle: { color: palette['cat-1'], opacity: 0.8 } },
    ],
  }
  const A = rf.loo.loo_A, B = rf.loo.loo_B

  return (
    <div className="space-y-4">
      <Card title="Rain that fell, and the gauges that measured it" subtitle="Station totals set how much; ERA5 sets when. Toggle the layers, click a gauge.">
        <div className="grid gap-3 md:grid-cols-4">
          <Stat label="Rain gauges used" value={n0(rf.n_gauges)} sub={`${rf.n_saih} SAIH + ${rf.n_aemet} AEMET`} />
          <Stat label="Leave-one-out error" value={`${n0(B.rmse_mm)} mm`} sub={`R² ${B.r2} · bias ${B.bias_mm} mm`} />
          <Stat label="Wettest gauge" value="621 mm" sub="Chiva (SAIH), Poyo headwaters" />
          <Stat label="Station coordinates" value={`${rf.n_saih - rf.n_approx_coords} / ${rf.n_saih}`} sub="SAIH gauges with exact position" />
        </div>
        <div className="mt-4"><LayerMap layers={layers} bounds={STUDY_BOUNDS} dark={dark} height={620}
          attribution="Rain: SAIH Júcar (CHJ), AEMET, ERA5 via Open-Meteo · Station layer © MITECO" /></div>
        <Info>
          Totals are the event totals from the CHJ report (SAIH, 28 Oct to 5 Nov) and AEMET daily values; 95 % is taken to fall in the 28–30 Oct model window
          (CHJ: 367 of 392 mm fell on 29 Oct in the Poyo). Amber points are gauges named in the report but missing from the 2014 SAIH station layer, placed at the
          municipality centre: the two wettest, Chiva and Real, are among them.
        </Info>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Hourly rainfall by catchment" subtitle="Gauge-interpolated totals distributed in time with the ERA5 hourly pattern (UTC; local time = UTC + 2).">
          <Chart option={hyOpt} height={320} label="Hourly catchment-mean rainfall for the four catchments" />
          <Legend palette={palette} items={names.map((n, i) => ({ label: n, role: SLOTS[i % 4], line: true }))} />
          <Info>The timing comes from ERA5 at 0.25°, which badly under-estimates the amounts (it gives about 40–120 mm where gauges recorded 300–700 mm) but is the only open hourly
            source. It is the weakest part of the forcing: replace it with the SAIH 5-minute series when available.</Info>
        </Card>
        <Card title="Does the interpolation work?" subtitle="Each gauge removed in turn and re-estimated from the others.">
          <Chart option={scOpt} height={320} label="Leave-one-out estimate versus gauge total" />
          <Info>
            Two ways of combining gauges and ERA5 were compared. Scaling ERA5 by an interpolated ratio: RMSE {n0(A.rmse_mm)} mm, R² {A.r2}.
            Interpolating the totals directly and using ERA5 only for timing (used here): RMSE <b>{n0(B.rmse_mm)} mm</b>, R² <b>{B.r2}</b>.
            ERA5 has the wrong spatial pattern, so gauges must set it.
          </Info>
        </Card>
      </div>

      <Card title="Catchment rainfall against the official figures" subtitle="Model field averaged over each catchment, against the CHJ report.">
        <DataTable name="the comparison" caption="Basin mean rainfall against CHJ" head={['Catchment (this study)', 'Area km²', 'Mean rain mm']}
          rows={rf.basin_means.map((b: { name: string; area_km2: number; mean_mm: number }) => [b.name, n0(b.area_km2), n0(b.mean_mm)])} />
        <Info>
          CHJ gives 392 mm for the Rambla del Poyo basin, 306 mm for the Magro basin and 142 mm for the Turia system, from its own interpolation of SAIH, AEMET and AVAMET gauges.
          The catchments here are defined from the terrain at the gauge sites, so they differ from CHJ's (the Poyo catchment above the A-3 gauge is 183 km², smaller than CHJ's), and the Turia
          is cut off by the study window. The comparison is a consistency check, not an independent validation: the same gauges feed both.
        </Info>
      </Card>
    </div>
  )
}
