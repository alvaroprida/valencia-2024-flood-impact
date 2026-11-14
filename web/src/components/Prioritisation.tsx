import { useEffect, useMemo, useState } from 'react'
import type { SiteData } from '../data'
import { n0 } from '../data'
import { FLOOD_BOUNDS, L, priorityLayer, TIER_COLORS } from '../layers'
import type { Palette } from '../theme'
import { dataUrl, LayerMap } from './LayerMap'
import { Card, DataTable, Info, Stat } from './ui'

type Feat = { type: 'Feature'; geometry: unknown; properties: Record<string, any> } // eslint-disable-line @typescript-eslint/no-explicit-any
type FC = { type: 'FeatureCollection'; features: Feat[] }

const KEYS = [
  ['people', 'People exposed', 'Severity-weighted people at ground level (0.25 for 0.3–0.5 m, 0.6 for 0.5–1 m, 1 for > 1 m).', 'c_people'],
  ['loss', 'Building loss', 'Modelled loss in the cell (percentile).', 'c_loss'],
  ['facility', 'Critical facilities', 'Flooded hospitals / care homes / fire & police (weight 3) and schools (2).', 'c_facility'],
  ['access', 'Access cut', 'Share of road length under ≥ 0.3 m of water (responders cannot get in).', 'c_access'],
] as const
type K = (typeof KEYS)[number][0]
const DEFAULT: Record<K, number> = { people: 45, loss: 20, facility: 20, access: 15 }

export function Prioritisation({ data, palette, dark }: { data: SiteData; palette: Palette; dark: boolean }) {
  const meta = data.summary.priority
  const [raw, setRaw] = useState<FC>()
  const [w, setW] = useState<Record<K, number>>(DEFAULT)
  useEffect(() => { fetch(dataUrl('priority_cells.geojson')).then((r) => r.json()).then(setRaw) }, [])

  const ranked = useMemo(() => {
    if (!raw) return undefined
    const tot = Object.values(w).reduce((a, b) => a + b, 0) || 1
    const feats: Feat[] = raw.features.map((f) => {
      const p = f.properties
      const score = (100 * (w.people * p.c_people + w.loss * p.c_loss + w.facility * p.c_facility + w.access * p.c_access)) / tot
      return { ...f, properties: { ...p, score } as Feat['properties'] }
    })
    const order = [...feats].sort((a, b) => b.properties.score - a.properties.score)
    const n = order.length
    order.forEach((f, i) => { f.properties.rank = i + 1; f.properties.tier = i < 0.05 * n ? 1 : i < 0.2 * n ? 2 : 3 })
    return { fc: { type: 'FeatureCollection', features: feats } as FC, order }
  }, [raw, w])

  const layers = useMemo(() => {
    const ls = [L.roadsCut(palette), L.facilities(), L.floodDepth(data.images.flood_depth), L.municipalities(palette)]
    if (ranked) ls.unshift(priorityLayer(ranked.fc))
    ls.find((l) => l.id === 'flood-depth')!.defaultOn = false
    ls.find((l) => l.id === 'fac')!.defaultOn = true
    return ls
  }, [ranked, palette, data.images])

  const byMuni = useMemo(() => {
    if (!ranked) return []
    const m = new Map<string, { t1: number; t2: number; ppl: number; loss: number; best: number }>()
    ranked.order.forEach((f) => {
      const p = f.properties, k = p.municipality ?? '–'
      const o = m.get(k) ?? { t1: 0, t2: 0, ppl: 0, loss: 0, best: 1e9 }
      if (p.tier === 1) o.t1++
      if (p.tier === 2) o.t2++
      o.ppl += p.people; o.loss += p.loss_k / 1000; o.best = Math.min(o.best, p.rank)
      m.set(k, o)
    })
    return [...m.entries()].sort((a, b) => b[1].t1 - a[1].t1 || a[1].best - b[1].best).slice(0, 12)
  }, [ranked])

  const top = ranked?.order.slice(0, 12) ?? []
  const sens = meta.sensitivity
  const changed = KEYS.some(([k]) => w[k] !== DEFAULT[k])

  return (
    <div className="space-y-4">
      <Card title="Where to send help first" subtitle="250 m cells ranked by a transparent score. Change the weights: the map, tiers and tables update.">
        <div className="grid gap-3 md:grid-cols-4">
          <Stat label="Cells ranked" value={n0(sens.cells_ranked)} sub="250 m cells with flooded buildings" />
          <Stat label="Tier 1" value={n0(Math.round(0.05 * (ranked?.order.length ?? sens.cells_ranked)))} sub="top 5 % of ranked cells" />
          <Stat label="Stability of the top 5 %" value={`${Math.round(sens.median_overlap_of_top5pct * 100)} %`} sub="median overlap under 500 random weightings" />
          <Stat label="Rank correlation" value={String(sens.median_rank_correlation)} sub="between random and default weights (Spearman)" />
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-[18rem_1fr]">
          <div className="space-y-3 rounded-lg border border-line bg-surface p-3 text-sm">
            <div className="font-semibold text-ink">Weights</div>
            {KEYS.map(([k, label, help]) => (
              <label key={k} className="block text-ink-2">
                <span className="flex justify-between"><span>{label}</span><b className="tabular text-ink">{Math.round((100 * w[k]) / Math.max(1, Object.values(w).reduce((a, b) => a + b, 0)))} %</b></span>
                <input type="range" min={0} max={100} value={w[k]} onChange={(e) => setW({ ...w, [k]: +e.target.value })} className="mt-0.5 w-full accent-[var(--accent)]" />
                <span className="block text-xs leading-snug text-ink-3">{help}</span>
              </label>
            ))}
            <button className="rounded-md border border-line px-2 py-1 text-xs text-ink-2 hover:text-ink disabled:opacity-40" disabled={!changed} onClick={() => setW(DEFAULT)}>Reset to defaults</button>
          </div>
          <LayerMap layers={layers} bounds={FLOOD_BOUNDS} dark={dark} height={640} attribution="SFINCS · Overture Maps · WorldPop · JRC" />
        </div>
        <Info>
          Each component is a percentile (0–1) over the affected cells; the score is their weighted sum, scaled to 100. Tier 1 is the top 5 % of cells, tier 2 the next 15 %.
          Facilities and road cuts are inputs, not outcomes: a cell with a flooded hospital outranks one with the same number of people but no critical facility.
        </Info>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Top cells" subtitle="Highest scores under the current weights.">
          <DataTable name="the ranking" caption="Top priority cells" head={['Rank', 'Municipality', 'People (ground)', 'Loss k€', 'Max depth m', 'Roads cut', 'Score']}
            rows={top.map((f) => { const p = f.properties; return [p.rank, p.municipality ?? '–', n0(p.people), n0(p.loss_k), p.maxd, `${Math.round(p.road_cut * 100)} %`, p.score.toFixed(1)] })} />
          <div className="mt-2 space-y-1 text-xs text-ink-2">
            {top.slice(0, 6).map((f) => f.properties.fac && (
              <div key={f.properties.rank}><b className="text-ink">#{f.properties.rank}</b> {String(f.properties.fac)}</div>))}
          </div>
        </Card>
        <Card title="Municipalities" subtitle="By number of tier-1 cells.">
          <DataTable name="the ranking" caption="Municipalities by tier-1 cells" head={['Municipality', 'Tier-1 cells', 'Tier-2 cells', 'People (ground)', 'Loss M€']}
            rows={byMuni.map(([k, o]) => [k, o.t1, o.t2, n0(o.ppl), n0(o.loss)])} />
          <div className="mt-3 flex gap-3 text-xs text-ink-3">{TIER_COLORS.map((c, i) => <span key={c} className="flex items-center gap-1"><span className="h-3 w-3 rounded-sm" style={{ background: c }} />Tier {i + 1}</span>)}</div>
        </Card>
      </div>

      <Card title="How to read this, and what it is not">
        <ul className="space-y-2 text-sm leading-relaxed text-ink-2">
          <li><b className="text-ink">A triage aid, not an order.</b> It ranks where the modelled flood meets people, value, critical facilities and cut roads. Local knowledge and live information decide.</li>
          <li><b className="text-ink">Weights are a judgement.</b> The defaults put people first (45 %). Across 500 random weightings the top 5 % of cells overlaps {Math.round(sens.median_overlap_of_top5pct * 100)} % (10th percentile {Math.round(sens.p10_overlap * 100)} %), so the head of the list is fairly stable, the tail is not.</li>
          <li><b className="text-ink">Inherits every upstream error:</b> over-predicted extent, inferred building use, and a population grid that is modelled, not counted.</li>
          <li><b className="text-ink">Not included:</b> vulnerability of people (age, mobility), vehicles in underpasses, car parks and basements, where the worst of the real event happened. A real tool would add them.</li>
        </ul>
      </Card>
    </div>
  )
}
