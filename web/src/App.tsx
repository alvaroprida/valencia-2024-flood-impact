import { useEffect, useState } from 'react'
import { Approach } from './components/Approach'
import { Exposure } from './components/Exposure'
import { FloodExtent } from './components/FloodExtent'
import { Impact } from './components/Impact'
import { Method } from './components/Method'
import { Model } from './components/Model'
import { Overview } from './components/Overview'
import { Prioritisation } from './components/Prioritisation'
import { RainfallGauges } from './components/RainfallGauges'
import { SatelliteLens } from './components/SatelliteLens'
import { Vulnerability } from './components/Vulnerability'
import { useSiteData } from './data'
import { usePalette } from './theme'

const TABS = [
  ['overview', 'Overview'],
  ['approach', 'Approach & sources'],
  ['satellite', 'Satellite evidence'],
  ['rainfall', 'Rainfall & gauges'],
  ['model', 'Flood model'],
  ['extent', 'Flood extent & depth'],
  ['exposure', 'Exposure'],
  ['vulnerability', 'Vulnerability'],
  ['impact', 'Impact'],
  ['priority', 'Prioritisation'],
  ['method', 'Method & sources'],
] as const
export type TabKey = (typeof TABS)[number][0]

/** Sub-tabs grouped under the Hazard tab (each keeps its own URL hash). */
const HAZARD: readonly TabKey[] = ['approach', 'satellite', 'rainfall', 'model', 'extent']
const label = (k: TabKey) => TABS.find(([t]) => t === k)![1]
const TOP: readonly (TabKey | 'hazard')[] = TABS.map(([k]) => k)
  .filter((k) => !HAZARD.includes(k) || k === HAZARD[0])
  .map((k) => (k === HAZARD[0] ? 'hazard' : k))

function initialTab(): TabKey {
  const h = window.location.hash.slice(1)
  return (TABS.find(([k]) => k === h)?.[0] ?? 'overview') as TabKey
}

export default function App() {
  const { palette, dark } = usePalette()
  const { data, error } = useSiteData()
  const [tab, setTab] = useState<TabKey>(initialTab)

  useEffect(() => {
    const onHash = () => setTab(initialTab())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const go = (k: TabKey) => {
    window.location.hash = k
    setTab(k)
    window.scrollTo({ top: 0 })
  }

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 md:p-6">
      <header>
        <p className="text-sm font-medium text-accent">Response · rapid flood impact mapping</p>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Valencia 2024 · The DANA flash floods</h1>
        <p className="max-w-3xl text-sm text-ink-2">
          What open satellite data can and cannot see of a flash flood, and how imagery, station rainfall, river gauges and
          a hydrodynamic model are combined into a flood extent and depth layer, then into building and population impact and a
          ranking of where to send emergency response first. Validated against Copernicus EMS activation EMSR773.
        </p>
      </header>

      <div role="note" className="rounded-lg bg-banner px-4 py-2 text-sm text-ink">
        <strong>Research case study, not an official map.</strong> Built only from open data after the event; every result tab
        shows how it scores against the independent Copernicus EMS reference, including where it fails.
      </div>

      <nav className="flex gap-1 overflow-x-auto border-b border-line" aria-label="Sections">
        {TOP.map((k) => {
          const active = k === 'hazard' ? HAZARD.includes(tab) : tab === k
          return (
            <button key={k} onClick={() => go(k === 'hazard' ? HAZARD[0] : k)} aria-current={active ? 'page' : undefined}
              className={`-mb-px shrink-0 border-b-2 px-3 py-2 text-sm ${active ? 'border-accent font-medium text-ink' : 'border-transparent text-ink-2 hover:text-ink'}`}>
              {k === 'hazard' ? 'Hazard' : label(k)}
            </button>
          )
        })}
      </nav>

      {HAZARD.includes(tab) && (
        <nav className="-mt-2 flex gap-1 overflow-x-auto border-b border-line" aria-label="Hazard sections">
          {HAZARD.map((k, i) => (
            <button key={k} onClick={() => go(k)} aria-current={tab === k ? 'page' : undefined}
              className={`-mb-px shrink-0 border-b-2 px-3 py-1.5 text-[13px] ${tab === k ? 'border-accent text-ink' : 'border-transparent text-ink-3 hover:text-ink'}`}>
              {i + 1} · {label(k)}
            </button>
          ))}
        </nav>
      )}

      {error && <div className="p-8 text-ink">Could not load data: {error}</div>}
      {!data && !error && <div className="p-8 text-ink-3">Loading…</div>}
      {data && (
        <main className="min-w-0">
          {tab === 'overview' && <Overview data={data} go={go} palette={palette} dark={dark} />}
          {tab === 'approach' && <Approach data={data} go={go} />}
          {tab === 'satellite' && <SatelliteLens data={data} palette={palette} dark={dark} />}
          {tab === 'rainfall' && <RainfallGauges data={data} palette={palette} dark={dark} />}
          {tab === 'model' && <Model data={data} palette={palette} />}
          {tab === 'extent' && <FloodExtent data={data} palette={palette} dark={dark} />}
          {tab === 'exposure' && <Exposure data={data} palette={palette} dark={dark} />}
          {tab === 'vulnerability' && <Vulnerability data={data} palette={palette} />}
          {tab === 'impact' && <Impact data={data} palette={palette} dark={dark} />}
          {tab === 'priority' && <Prioritisation data={data} palette={palette} dark={dark} />}
          {tab === 'method' && <Method data={data} />}
        </main>
      )}

      <footer className="pt-4 text-sm text-ink-3">
        © 2026 Alvaro Prida · Site code under the MIT licence; data and figures follow the licences of their sources (see Method &amp; sources).
        Research work in progress, not an official hazard, damage or response map.
      </footer>
    </div>
  )
}
