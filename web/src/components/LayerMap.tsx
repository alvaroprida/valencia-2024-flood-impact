import { setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useMemo, useState, type ReactNode } from 'react'
import Map, { Layer, Popup, Source, type MapLayerMouseEvent } from 'react-map-gl/maplibre'

setWorkerUrl(workerUrl)

const BASEMAP = {
  light: 'https://tiles.openfreemap.org/styles/positron',
  dark: 'https://tiles.openfreemap.org/styles/dark',
}

export const dataUrl = (name: string) => `${import.meta.env.BASE_URL}data/${name}`

type Paint = Record<string, unknown>
export interface LegendItem { color: string; label: string; shape?: 'box' | 'line' | 'dot' }

/** One toggleable map layer. `data` is a GeoJSON URL; `image` is a pre-coloured PNG draped on the map. */
export interface MapLayer {
  id: string
  label: string
  group: string
  kind: 'fill' | 'line' | 'circle' | 'image'
  data?: string | object
  image?: { url: string; coordinates: [[number, number], [number, number], [number, number], [number, number]] }
  paint?: Paint
  layout?: Paint
  filter?: unknown[]
  minzoom?: number
  defaultOn?: boolean
  opacity?: number
  legend?: LegendItem[]
  /** Properties shown in the popup on click (label -> formatter). */
  popup?: (props: Record<string, unknown>) => ReactNode
  note?: ReactNode
}

function LegendSwatch({ item }: { item: LegendItem }) {
  const cls = item.shape === 'line' ? 'h-0.5 w-4 rounded' : item.shape === 'dot' ? 'h-2.5 w-2.5 rounded-full' : 'h-3 w-3 rounded-sm'
  return <span className={`${cls} shrink-0`} style={{ background: item.color }} aria-hidden />
}

/** Map with a layer panel: every layer can be switched on or off, with its legend and a click popup. */
export function LayerMap({ layers, bounds, dark, height = 640, attribution, toolbar }: {
  layers: MapLayer[]
  bounds: [[number, number], [number, number]]
  dark: boolean
  height?: number
  attribution?: string
  toolbar?: ReactNode
}) {
  const [on, setOn] = useState<Record<string, boolean>>(() => Object.fromEntries(layers.map((l) => [l.id, !!l.defaultOn])))
  const [popup, setPopup] = useState<{ lng: number; lat: number; layer: MapLayer; props: Record<string, unknown> }>()
  const interactive = useMemo(() => layers.filter((l) => l.popup).map((l) => `${l.id}-layer`), [layers])
  const groups = useMemo(() => {
    const g: Record<string, MapLayer[]> = {}
    layers.forEach((l) => (g[l.group] ??= []).push(l))
    return Object.entries(g)
  }, [layers])

  const onClick = (e: MapLayerMouseEvent) => {
    const f = e.features?.[0]
    if (!f) return setPopup(undefined)
    const layer = layers.find((l) => `${l.id}-layer` === f.layer.id)
    if (layer) setPopup({ lng: e.lngLat.lng, lat: e.lngLat.lat, layer, props: (f.properties ?? {}) as Record<string, unknown> })
  }

  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_17rem]">
      <div className="relative overflow-hidden rounded-lg border border-line" style={{ height }}>
        <Map
          initialViewState={{ bounds, fitBoundsOptions: { padding: 12 } }}
          mapStyle={dark ? BASEMAP.dark : BASEMAP.light}
          onLoad={(e) => e.target.resize()}
          interactiveLayerIds={interactive}
          onClick={onClick}
          attributionControl={{ compact: true, customAttribution: attribution }}
        >
          {layers.map((l) => {
            const vis = on[l.id] ? 'visible' : 'none'
            if (l.kind === 'image' && l.image) {
              return (
                <Source key={l.id} id={l.id} type="image" url={l.image.url} coordinates={l.image.coordinates}>
                  <Layer id={`${l.id}-layer`} type="raster" layout={{ visibility: vis }}
                    paint={{ 'raster-opacity': l.opacity ?? 0.8, 'raster-resampling': 'nearest' }} />
                </Source>
              )
            }
            if (!l.data) return null
            return (
              <Source key={l.id} id={l.id} type="geojson" data={l.data}>
                <Layer id={`${l.id}-layer`} type={l.kind as 'fill' | 'line' | 'circle'}
                  layout={{ visibility: vis, ...(l.layout ?? {}) } as never}
                  paint={(l.paint ?? {}) as never}
                  {...(l.filter ? { filter: l.filter as never } : {})}
                  {...(l.minzoom ? { minzoom: l.minzoom } : {})} />
              </Source>
            )
          })}
          {popup && (
            <Popup longitude={popup.lng} latitude={popup.lat} onClose={() => setPopup(undefined)} closeButton closeOnClick={false} maxWidth="280px">
              <div className="text-sm leading-snug text-ink">{popup.layer.popup?.(popup.props)}</div>
            </Popup>
          )}
        </Map>
      </div>

      <aside className="max-h-[640px] space-y-3 overflow-y-auto rounded-lg border border-line bg-surface p-3 text-sm" aria-label="Map layers">
        {toolbar}
        {groups.map(([group, ls]) => (
          <fieldset key={group} className="space-y-1.5">
            <legend className="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-3">{group}</legend>
            {ls.map((l) => (
              <div key={l.id}>
                <label className="flex cursor-pointer items-start gap-2 text-ink">
                  <input type="checkbox" className="mt-1 accent-[var(--accent)]" checked={!!on[l.id]}
                    onChange={(e) => setOn((s) => ({ ...s, [l.id]: e.target.checked }))} />
                  <span>{l.label}</span>
                </label>
                {on[l.id] && l.legend && (
                  <ul className="ml-6 mt-1 space-y-0.5 text-xs text-ink-2">
                    {l.legend.map((it) => (
                      <li key={it.label} className="flex items-center gap-1.5"><LegendSwatch item={it} />{it.label}</li>
                    ))}
                  </ul>
                )}
                {on[l.id] && l.note && <p className="ml-6 mt-1 text-xs leading-relaxed text-ink-3">{l.note}</p>}
              </div>
            ))}
          </fieldset>
        ))}
      </aside>
    </div>
  )
}
