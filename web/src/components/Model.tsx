import type { EChartsOption } from 'echarts'
import type { SiteData } from '../data'
import { n0 } from '../data'
import type { Palette } from '../theme'
import { Card, Chart, DataTable, Info, Legend, Stat } from './ui'

const SETUP: [string, string][] = [
  ['Engine', 'SFINCS v2.4.1 (Deltares), reduced-physics shallow-water solver with subgrid tables; rain-on-grid, as in the Madagascar study.'],
  ['Domain', 'Rambla del Poyo and Magro catchments, plus the Horta Sud and Ribera plain down to the coast: about 2,870 km² of active cells.'],
  ['Grid', '90 m cells with 45 m subgrid pixels, from FABDEM V1-2 (30 m, buildings and forests removed).'],
  ['Rainfall', 'Hourly gauge-interpolated field, 28 Oct 12:00 to 30 Oct 12:00 UTC (see Rainfall & gauges).'],
  ['Infiltration', 'SCS curve number from ESA WorldCover classes, hydrologic soil group C assumed everywhere, average antecedent moisture. A literature lookup: uncertain, calibrated.'],
  ['Roughness', 'Manning n from WorldCover (0.03 bare to 0.15 trees; 0.12 built-up; WorldCover calls the citrus orchards "trees").'],
  ['Boundaries', 'Mediterranean fixed at +0.3 m. The Albufera is a managed lake: held at sea level, because FABDEM cannot resolve its sluices and it would otherwise fill with runoff.'],
  ['Not represented', 'Sewers and street drainage, culverts and bridges, levees, the Forata, Loriguilla and Benagéber dams, the Turia diversion and irrigation canals, buildings as obstacles. These matter most in the dense Horta Sud streets.'],
]

export function Model({ data, palette }: { data: SiteData; palette: Palette }) {
  const m = data.summary.model
  const runs = m.runs as Record<string, any> // eslint-disable-line @typescript-eslint/no-explicit-any
  const specs = (m.specs ?? {}) as Record<string, { cn: number; rain: number; man: number }>
  const final = data.summary.final_run as string
  const names = Object.keys(runs)
  const fin = runs[final]
  const rows = names.map((k) => {
    const r = runs[k]
    const sp = specs[k]
    const cal = r['Algemesi (AOI04)'], val = r['Horta Sud (AOI03)']
    return [k + (k === final ? ' ✓' : ''), sp ? `${sp.cn >= 0 ? '+' : ''}${sp.cn}` : '–', sp ? sp.rain.toFixed(2) : '–', sp ? sp.man.toFixed(2) : '–',
      cal.csi, `${Math.round(cal.recall * 100)} %`, `${cal.area_ratio_model_to_obs}×`, val.csi, `${Math.round(val.recall * 100)} %`, `${val.area_ratio_model_to_obs}×`,
      r.water_balance ? `${Math.round(r.water_balance.infiltrated_share * 100)} %` : '–']
  })

  const hg = m.hydrograph as { gauges: { name: string; observed_peak: number; observed_time: string; modelled_peak: number; modelled_time: string; series: [string, number][] }[] } | undefined
  const hgOpt: EChartsOption | undefined = hg && {
    grid: { left: 56, right: 16, top: 24, bottom: 56 },
    tooltip: { trigger: 'axis', valueFormatter: (v) => `${Math.round(Number(v))} m³/s` },
    xAxis: { type: 'category', data: hg.gauges[0].series.map((s) => s[0]), axisLabel: { color: palette['text-muted'], interval: 11 } },
    yAxis: { type: 'value', name: 'm³/s', axisLabel: { color: palette['text-muted'] }, splitLine: { lineStyle: { color: palette.grid } } },
    series: hg.gauges.map((g, i) => ({ name: g.name, type: 'line', showSymbol: false, data: g.series.map((s) => s[1]), lineStyle: { color: palette[(['cat-1', 'cat-2', 'cat-3'] as const)[i % 3]] },
      markPoint: { data: [{ name: 'observed peak', coord: [g.observed_time, g.observed_peak] }], symbolSize: 10, itemStyle: { color: palette[(['cat-1', 'cat-2', 'cat-3'] as const)[i % 3]] } } })),
  }

  return (
    <div className="space-y-4">
      <Card title="A rain-on-grid model of the Poyo, Magro and Horta Sud" subtitle="The step that fills in what no sensor saw.">
        <div className="grid gap-3 md:grid-cols-4">
          <Stat label="Active cells" value="353,846" sub="90 m, 45 m subgrid" />
          <Stat label="Simulated" value="48 h" sub="28 Oct 12:00 → 30 Oct 12:00 UTC" />
          <Stat label="Run time" value="≈ 18 min" sub="12 cores, Linux binary under WSL1" />
          <Stat label="Chosen run" value={final} sub={fin?.water_balance ? `${Math.round(fin.water_balance.infiltrated_share * 100)} % of rain infiltrated` : ''} />
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <tbody>{SETUP.map(([k, v]) => (
              <tr key={k} className="border-b border-line align-top last:border-0"><td className="w-40 py-2 pr-4 font-medium text-ink">{k}</td><td className="py-2 text-ink-2">{v}</td></tr>))}</tbody>
          </table>
        </div>
      </Card>

      <Card title="Calibration and held-out test" subtitle="Parameters were tuned to Algemesí (CEMS AOI04) only. Horta Sud (AOI03) is the held-out test.">
        <DataTable name="all runs" caption="Calibration variants and their scores" head={['Run', 'CN shift', 'Rain ×', 'Manning ×', 'CSI', 'Recall', 'Area ×', 'CSI', 'Recall', 'Area ×', 'Infiltrated']} rows={rows} />
        <Info>
          Columns 5–7: Algemesí (calibration). Columns 8–10: Horta Sud (held out). <i>CSI</i> is hits ÷ (hits + misses + false alarms): 1 is perfect, and values above ~0.4 are rare
          for flash floods. <i>Area ×</i> is modelled over observed flooded area inside the CEMS-analysed footprint (1 is unbiased).
          Flooded means depth ≥ 0.3 m in clusters ≥ 1 ha, applied identically to every run.
        </Info>
        {hg && hgOpt && (
          <div className="mt-4">
            <h3 className="mb-1 text-sm font-semibold text-ink">Modelled discharge at the river gauges</h3>
            <Chart option={hgOpt} height={300} label="Modelled hydrographs at the river gauges, observed peaks marked" />
            <Legend palette={palette} items={hg.gauges.map((g, i) => ({ label: `${g.name}: observed ${n0(g.observed_peak)} m³/s (${g.observed_time}), model ${n0(g.modelled_peak)} (${g.modelled_time})`, role: (['cat-1', 'cat-2', 'cat-3'] as const)[i % 3], line: true }))} />
          </div>
        )}
      </Card>

      <Card title="What the model cannot do" subtitle="Stated so the maps are read correctly.">
        <ul className="space-y-2 text-sm leading-relaxed text-ink-2">
          <li><b className="text-ink">Street-scale flooding.</b> At 90 m cells with no drainage network the dense Horta Sud streets are poorly resolved; this is the main source of missed flooding.</li>
          <li><b className="text-ink">Over-prediction on flat ground.</b> Without sewers and ditches, rain pools on flat farmland and the lower plain: the model floods too much area (see the area ratios above).</li>
          <li><b className="text-ink">Rainfall timing.</b> The hourly pattern comes from ERA5, not gauges. A few hours of error moves the flood peak.</li>
          <li><b className="text-ink">Uncertain parameters.</b> Curve number, roughness and a rainfall scaling were varied within plausible ranges; the spread is in the table, and it is the honest uncertainty of the flood layer.</li>
        </ul>
      </Card>
    </div>
  )
}
