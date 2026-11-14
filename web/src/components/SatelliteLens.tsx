import { useMemo } from 'react'
import type { SiteData } from '../data'
import { n1, pct } from '../data'
import { L, STUDY_BOUNDS } from '../layers'
import type { Palette } from '../theme'
import { Card, DataTable, Info, Stat } from './ui'
import { LayerMap } from './LayerMap'

const PASSES: [string, string, string, string][] = [
  ['25 Oct', 'Sentinel-1 (desc. orbit 8)', 'Baseline', 'Dry, before the event'],
  ['26 Oct', 'Sentinel-2', 'Baseline', 'Clear: pre-event water mask'],
  ['29 Oct', '—', 'Event', 'Flood peak in the afternoon and evening (local time)'],
  ['30 Oct', 'Landsat 8', 'Unusable', '≈ 1 % clear over the study area'],
  ['31 Oct', 'Sentinel-2', 'Partial', '≈ 43 % clear; CEMS very-high-resolution images the same morning'],
  ['1 Nov', 'Sentinel-1 (desc. orbit 110)', 'Used', 'First post-event radar pass, ~3 days after the peak'],
  ['5–6 Nov', 'Sentinel-2, Sentinel-1', 'Late', 'Flood has receded; used as a second look'],
]

export function SatelliteLens({ data, palette, dark }: { data: SiteData; palette: Palette; dark: boolean }) {
  const s1 = data.summary.satellite.s1['20241101']
  const s2 = data.summary.satellite.s2['20241031']
  const layers = useMemo(() => [
    L.s1(data.images.s1_flood), L.s2(data.images.s2_flood), L.cemsObserved(palette), L.cemsFootprint(palette),
    L.basins(palette), L.streams(palette, false), L.albufera(palette),
  ], [data.images, palette])
  // show the CEMS reference by default so the miss is obvious
  layers[2].defaultOn = true
  layers[0].defaultOn = true

  const v1 = s1.validation_vs_cems_vhr
  const v2 = s2.vs_cems_vhr_clear_pixels_only
  return (
    <div className="space-y-4">
      <Card title="What the open satellites saw" subtitle="Flood detection from Sentinel-1 radar and Sentinel-2 optical, against the Copernicus EMS very-high-resolution outlines.">
        <div className="grid gap-3 md:grid-cols-4">
          <Stat label="Sentinel-1, 1 Nov: recall" value={pct(v1.recall, 1)} sub={`precision ${pct(v1.precision, 1)} · ${n1(v1.tp_km2)} km² hit`} />
          <Stat label="Sentinel-2, 31 Oct: recall" value={pct(v2.recall, 0)} sub={`on clear pixels only (${pct(s2.clear_share_of_footprint)} clear)`} />
          <Stat label="Radar false alarms" value={`${n1(v1.fp_km2)} km²`} sub="mostly Albufera rice paddies" />
          <Stat label="First post-event radar" value="+3 days" sub="no Sentinel-1 scene 27–31 Oct" />
        </div>
        <div className="mt-4">
          <LayerMap layers={layers} bounds={STUDY_BOUNDS} dark={dark} height={600}
            attribution="Contains modified Copernicus Sentinel data 2024 · Copernicus EMS EMSR773" />
        </div>
        <Info>
          Switch the layers on and off. The orange (radar) and green (optical) detections barely overlap the CEMS flood (red outline):
          the radar found the managed Albufera rice paddies, not the Horta Sud streets, and the optical scene is mostly under cloud
          where the flood was. Both scores are computed inside the area CEMS analysed (dashed outline).
        </Info>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Why the radar missed it" subtitle="Four reasons, each visible in the data.">
          <ul className="space-y-2 text-sm leading-relaxed text-ink-2">
            <li><b className="text-ink">Revisit.</b> Sentinel-1 did not pass between 26 Oct and 1 Nov. By the 1 Nov pass the water in the Horta Sud streets and orchards had drained.</li>
            <li><b className="text-ink">Urban and orchard flooding.</b> Water between buildings and under trees is not dark in radar: it can even be bright (double bounce).</li>
            <li><b className="text-ink">Managed flooding.</b> The Albufera rice fields are flooded on purpose each autumn, which dominates the change signal ({n1(v1.fp_km2)} km² of false alarms).</li>
            <li><b className="text-ink">Thresholds.</b> Fixed physical thresholds were used (change ≤ −3 dB and Otsu, {s1.threshold_vv_db} dB VV), not tuned on the reference.</li>
          </ul>
        </Card>
        <Card title="Why the optical missed it" subtitle="Cloud and timing.">
          <ul className="space-y-2 text-sm leading-relaxed text-ink-2">
            <li><b className="text-ink">Cloud.</b> On 31 Oct only {pct(s2.clear_share_of_footprint)} of the validation area was cloud-free, and the cloud sat over the Horta Sud plain.</li>
            <li><b className="text-ink">Clear pixels.</b> Where the sky was clear, recall was {pct(v2.recall)} (precision {pct(v2.precision)}): muddy, shallow or urban water does not stand out in the water index.</li>
            <li><b className="text-ink">Landsat 8</b> on 30 Oct was cloud-covered ({'≈'} 1 % clear).</li>
          </ul>
        </Card>
      </div>

      <Card title="Scene availability" subtitle="From the Microsoft Planetary Computer catalogue, 25 Oct to 7 Nov 2024.">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-line text-left text-ink-3"><th className="py-1.5 pr-4 font-medium">Date (2024)</th><th className="py-1.5 pr-4 font-medium">Sensor</th><th className="py-1.5 pr-4 font-medium">Role</th><th className="py-1.5 font-medium">Note</th></tr></thead>
            <tbody>{PASSES.map((r) => (
              <tr key={r[0]} className="border-b border-line last:border-0"><td className="py-1.5 pr-4 text-ink">{r[0]}</td><td className="py-1.5 pr-4 text-ink-2">{r[1]}</td>
                <td className="py-1.5 pr-4 text-ink-2">{r[2]}</td><td className="py-1.5 text-ink-2">{r[3]}</td></tr>))}</tbody>
          </table>
        </div>
        <DataTable name="the satellite scores" caption="Satellite detection scores against CEMS" head={['Product', 'Precision', 'Recall', 'F1', 'CSI', 'Hit km²', 'False alarm km²', 'Missed km²']}
          rows={[
            ['Sentinel-1, 1 Nov', pct(v1.precision, 1), pct(v1.recall, 1), v1.f1, v1.csi, n1(v1.tp_km2), n1(v1.fp_km2), n1(v1.fn_km2)],
            ['Sentinel-2, 31 Oct (clear pixels)', pct(v2.precision, 1), pct(v2.recall, 1), v2.f1, v2.csi, n1(v2.tp_km2), n1(v2.fp_km2), n1(v2.fn_km2)],
          ]} />
      </Card>

      <Card title="What this changes">
        <p className="max-w-4xl text-sm leading-relaxed text-ink-2">
          Open satellite imagery is essential for slow river floods, and for the days after. For a flash flood it arrives after the peak,
          so it cannot be the primary source of the maximum extent. The next tabs use the rainfall, the gauges and a hydrodynamic model to fill the gap,
          and use the satellites for what they do well: to check the model, and to say where it cannot be checked.
        </p>
      </Card>
    </div>
  )
}
