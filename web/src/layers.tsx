import type { ReactNode } from 'react'
import { dataUrl, type MapLayer } from './components/LayerMap'
import { DAMAGE_RAMP, DEPTH_RAMP, type Palette } from './theme'

export type Corners = [[number, number], [number, number], [number, number], [number, number]]
export type Images = Record<'flood_depth' | 's1_flood' | 's2_flood' | 'rain_total', Corners>

/** Study area (lon/lat): Poyo + Magro catchments, Horta Sud, Ribera, Albufera. */
export const STUDY_BOUNDS: [[number, number], [number, number]] = [[-0.98, 39.12], [-0.27, 39.58]]
export const FLOOD_BOUNDS: [[number, number], [number, number]] = [[-0.68, 39.17], [-0.28, 39.55]]

export const OCC = ['residential', 'commercial', 'industrial', 'public', 'agricultural', 'other'] as const

const n0 = (v: unknown) => (typeof v === 'number' ? Math.round(v).toLocaleString('en') : String(v ?? '–'))
const Row = ({ k, v }: { k: string; v: ReactNode }) => (
  <div className="flex justify-between gap-4"><span className="text-ink-3">{k}</span><span className="tabular text-right">{v}</span></div>
)
const Title = ({ children }: { children: ReactNode }) => <div className="mb-1 font-semibold">{children}</div>

export const L = {
  basins: (p: Palette, on = true): MapLayer => ({
    id: 'basins', label: 'Catchments (from FABDEM)', group: 'Reference', kind: 'line', data: dataUrl('basins.geojson'), defaultOn: on,
    paint: { 'line-color': p.accent, 'line-width': 2, 'line-dasharray': [3, 2] },
    legend: [{ color: p.accent, label: 'Catchment outline', shape: 'line' }],
    popup: (x) => <><Title>{String(x.name)}</Title><Row k="Area" v={`${n0(x.area_km2)} km²`} /><Row k="Mean rainfall, model" v={`${n0(x.mean_rain_mm)} mm`} /></>,
  }),
  basinFill: (p: Palette): MapLayer => ({
    id: 'basinfill', label: 'Catchments (filled)', group: 'Reference', kind: 'fill', data: dataUrl('basins.geojson'), defaultOn: false,
    paint: { 'fill-color': p.accent, 'fill-opacity': 0.08 },
  }),
  streams: (p: Palette, on = true): MapLayer => ({
    id: 'streams', label: 'Rivers and creeks (> 5 km²)', group: 'Reference', kind: 'line', data: dataUrl('streams.geojson'), defaultOn: on,
    paint: { 'line-color': p['cat-1'], 'line-opacity': 0.85,
      'line-width': ['interpolate', ['linear'], ['get', 'acc_km2'], 5, 0.6, 100, 1.4, 1000, 2.6] },
    legend: [{ color: p['cat-1'], label: 'Stream network (width = drainage area)', shape: 'line' }],
  }),
  albufera: (p: Palette): MapLayer => ({
    id: 'albufera', label: 'Albufera lake (held at sea level in the model)', group: 'Reference', kind: 'fill', data: dataUrl('albufera.geojson'), defaultOn: false,
    paint: { 'fill-color': p['cat-3'], 'fill-opacity': 0.25, 'fill-outline-color': p['cat-3'] },
  }),
  gauges: (p: Palette): MapLayer[] => {
    const rain = ['==', ['get', 'kind'], 'rain']
    const col = (c: string) => ({ 'circle-color': c, 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 1 })
    const pop = (x: Record<string, unknown>) => (
      <>
        <Title>{String(x.name)}</Title>
        {x.event_mm != null && <Row k="Event total" v={`${n0(x.event_mm)} mm`} />}
        {x.report_text && x.kind !== 'rain_aemet' && <div className="mt-1 text-xs text-ink-2">{String(x.report_text)}</div>}
        {x.peak_q != null && <Row k="Peak (CHJ)" v={`${n0(x.peak_q)} m³/s · ${x.peak_time}`} />}
        <Row k="Coordinates" v={String(x.coord_quality)} />
        <div className="mt-1 text-xs text-ink-3">{String(x.source)}</div>
      </>
    )
    return [
      { id: 'g-rain', label: 'Rain gauges, SAIH (exact coordinates)', group: 'Gauges', kind: 'circle', data: dataUrl('gauges.geojson'), defaultOn: true,
        filter: ['all', rain, ['==', ['get', 'coord_quality'], 'exact']],
        paint: { ...col(p['cat-3']), 'circle-radius': ['interpolate', ['linear'], ['coalesce', ['get', 'event_mm'], 0], 0, 3, 300, 5, 650, 9] },
        legend: [{ color: p['cat-3'], label: 'size = event total (mm)', shape: 'dot' }], popup: pop },
      { id: 'g-rain-approx', label: 'Rain gauges, SAIH (approximate: municipality centre)', group: 'Gauges', kind: 'circle', data: dataUrl('gauges.geojson'), defaultOn: true,
        filter: ['all', rain, ['==', ['get', 'coord_quality'], 'approx']],
        paint: { ...col(p['cat-4']), 'circle-radius': ['interpolate', ['linear'], ['coalesce', ['get', 'event_mm'], 0], 0, 3, 300, 5, 650, 9] },
        note: 'Not in the 2014 SAIH station layer; placed at the municipality centre, so up to a few km off.', popup: pop },
      { id: 'g-aemet', label: 'Rain stations, AEMET (daily total, 29 Oct)', group: 'Gauges', kind: 'circle', data: dataUrl('gauges.geojson'), defaultOn: true,
        filter: ['==', ['get', 'kind'], 'rain_aemet'],
        paint: { ...col(p['cat-5']), 'circle-radius': ['interpolate', ['linear'], ['coalesce', ['get', 'event_mm'], 0], 0, 3, 300, 6, 800, 10] }, popup: pop },
      { id: 'g-q', label: 'River gauges (discharge)', group: 'Gauges', kind: 'circle', data: dataUrl('gauges.geojson'), defaultOn: true,
        filter: ['==', ['get', 'kind'], 'discharge'],
        paint: { 'circle-color': p['cat-2'], 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 1,
          'circle-radius': ['case', ['has', 'peak_q'], 7, 4] },
        legend: [{ color: p['cat-2'], label: 'larger = peak flow reported by CHJ', shape: 'dot' }], popup: pop },
      { id: 'g-res', label: 'Reservoirs', group: 'Gauges', kind: 'circle', data: dataUrl('gauges.geojson'), defaultOn: false,
        filter: ['==', ['get', 'kind'], 'reservoir'],
        paint: { 'circle-color': p.neutral, 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 1, 'circle-radius': 5 }, popup: pop },
    ]
  },
  municipalities: (p: Palette): MapLayer => ({
    id: 'muni', label: 'Municipalities (Overture)', group: 'Reference', kind: 'line', data: dataUrl('municipalities.geojson'), defaultOn: false,
    paint: { 'line-color': p['text-secondary'], 'line-width': 0.8, 'line-opacity': 0.7 },
    popup: (x) => <><Title>{String(x.municipality)}</Title>
      {x.buildings != null && <><Row k="Flooded buildings" v={n0(x.buildings)} /><Row k="People in flooded buildings" v={n0(x.people)} /><Row k="Loss (2010 €)" v={`${(Number(x.loss_meur)).toFixed(0)} M€`} /></>}</>,
  }),
  floodDepth: (img: Corners | undefined): MapLayer => ({
    id: 'flood-depth', label: 'Modelled maximum flood depth', group: 'Hazard', kind: 'image', defaultOn: true, opacity: 0.85,
    image: img ? { url: dataUrl('flood_depth.png'), coordinates: img } : undefined,
    legend: DEPTH_RAMP.map((d) => ({ color: d.color, label: d.label })),
    note: 'Depth ≥ 0.3 m, clusters ≥ 1 ha. 30 m, SFINCS rain-on-grid.',
  }),
  rainTotal: (img: Corners | undefined): MapLayer => ({
    id: 'rain-total', label: 'Rainfall total 28–30 Oct (gauge-interpolated)', group: 'Rainfall', kind: 'image', defaultOn: true, opacity: 0.75,
    image: img ? { url: dataUrl('rain_total.png'), coordinates: img } : undefined,
    legend: [{ color: '#c7e9b4', label: '≈ 100 mm' }, { color: '#41b6c4', label: '≈ 350 mm' }, { color: '#253494', label: '≥ 600 mm' }],
  }),
  cemsObserved: (p: Palette): MapLayer => ({
    id: 'cems', label: 'CEMS EMSR773 observed flood (reference)', group: 'Reference flood (Copernicus EMS)', kind: 'fill', data: dataUrl('cems_observed.geojson'), defaultOn: false,
    paint: { 'fill-color': p['cat-2'], 'fill-opacity': 0.35, 'fill-outline-color': p['cat-2'] },
    legend: [{ color: p['cat-2'], label: 'Flooded area + flood trace, very-high-resolution imagery, 31 Oct' }],
    popup: (x) => <><Title>{String(x.kind)}</Title><div className="text-xs text-ink-3">{String(x.aoi)} · CEMS EMSR773, 31 Oct 2024</div></>,
  }),
  cemsFootprint: (p: Palette): MapLayer => ({
    id: 'cems-foot', label: 'Area analysed by CEMS (validation area)', group: 'Reference flood (Copernicus EMS)', kind: 'line', data: dataUrl('cems_footprint.geojson'), defaultOn: false,
    paint: { 'line-color': p['cat-2'], 'line-width': 1.5, 'line-dasharray': [2, 2] },
  }),
  s1: (img: Corners | undefined): MapLayer => ({
    id: 's1', label: 'Sentinel-1 flood detection, 1 Nov', group: 'Satellite detections', kind: 'image', defaultOn: false, opacity: 0.8,
    image: img ? { url: dataUrl('s1_flood_20241101.png'), coordinates: img } : undefined,
    legend: [{ color: '#eb6834', label: 'new low-backscatter water vs Oct baseline' }],
    note: 'Mostly the Albufera rice paddies, flooded on purpose each autumn. Almost nothing in Horta Sud.',
  }),
  s2: (img: Corners | undefined): MapLayer => ({
    id: 's2', label: 'Sentinel-2 flood detection, 31 Oct', group: 'Satellite detections', kind: 'image', defaultOn: false, opacity: 0.8,
    image: img ? { url: dataUrl('s2_flood_20241031.png'), coordinates: img } : undefined,
    legend: [{ color: '#1baf7a', label: 'MNDWI water, new vs 26 Oct' }],
    note: 'Cloud hides most of the Horta Sud flood on 31 Oct.',
  }),
  exposureGrid: (): MapLayer => ({
    id: 'exp-grid', label: 'Population per 250 m cell (WorldPop → buildings)', group: 'Exposure', kind: 'fill', data: dataUrl('exposure_grid.geojson'), defaultOn: true,
    paint: { 'fill-color': ['interpolate', ['linear'], ['get', 'people'], 5, '#e9e4f7', 150, '#b9a9e2', 500, '#7a5cc4', 1500, '#452e7c', 4000, '#1b0f3b'],
      'fill-opacity': 0.75 },
    legend: [{ color: '#e9e4f7', label: '5 people' }, { color: '#7a5cc4', label: '500' }, { color: '#1b0f3b', label: '≥ 4,000' }],
    popup: (x) => <><Title>250 m cell</Title><Row k="People (est.)" v={n0(x.people)} /><Row k="Buildings" v={n0(x.buildings)} />
      <Row k="Residential share" v={`${Math.round(Number(x.residential) * 100)} %`} /><Row k="Industrial share" v={`${Math.round(Number(x.industrial) * 100)} %`} />
      <Row k="Mean floors" v={String(x.floors)} /></>,
  }),
  exposureResidential: (): MapLayer => ({
    id: 'exp-res', label: 'Residential share of buildings', group: 'Exposure', kind: 'fill', data: dataUrl('exposure_grid.geojson'), defaultOn: false,
    paint: { 'fill-color': ['interpolate', ['linear'], ['get', 'residential'], 0, '#d95926', 0.5, '#f2e6a0', 1, '#1baf7a'], 'fill-opacity': 0.7 },
    legend: [{ color: '#d95926', label: 'mostly industrial / other' }, { color: '#1baf7a', label: 'mostly residential' }],
  }),
  buildings: (): MapLayer => ({
    id: 'bld', label: 'Flooded buildings, coloured by damage ratio', group: 'Impact', kind: 'circle', data: dataUrl('buildings_flooded.geojson'), defaultOn: true,
    paint: {
      'circle-color': ['step', ['get', 'r'], DAMAGE_RAMP[0].color, 0.1, DAMAGE_RAMP[1].color, 0.3, DAMAGE_RAMP[2].color, 0.6, DAMAGE_RAMP[3].color],
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 0.8, 13, 2.2, 16, 5], 'circle-opacity': 0.9,
    },
    legend: DAMAGE_RAMP.map((d) => ({ color: d.color, label: d.label, shape: 'dot' as const })),
    popup: (x) => <><Title>Flooded building</Title><Row k="Use" v={OCC[Number(x.o)]} /><Row k="Depth" v={`${x.d} m`} /><Row k="Storeys" v={String(x.f)} />
      <Row k="Damage ratio" v={`${Math.round(Number(x.r) * 100)} %`} /><Row k="People (est.)" v={String(x.p)} /><Row k="Loss, 2010 €" v={`${n0(Number(x.l) * 1000)}`} /></>,
  }),
  cemsDamage: (p: Palette): MapLayer => ({
    id: 'cems-dmg', label: 'CEMS building damage grades (Horta Sud)', group: 'Reference flood (Copernicus EMS)', kind: 'circle', data: dataUrl('cems_damage_points.geojson'), defaultOn: false,
    paint: { 'circle-color': ['match', ['get', 'grade'], 'Destroyed', '#8c1c13', 'Damaged', p['cat-2'], p['cat-4']],
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 0.8, 14, 2.5, 17, 5], 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 0.3 },
    legend: [{ color: '#8c1c13', label: 'Destroyed', shape: 'dot' }, { color: p['cat-2'], label: 'Damaged', shape: 'dot' }, { color: p['cat-4'], label: 'Possibly damaged', shape: 'dot' }],
    popup: (x) => <><Title>{String(x.grade)}</Title><div className="text-xs text-ink-3">CEMS EMSR773 grading, photo-interpretation</div></>,
  }),
  impactMunicipalities: (): MapLayer => ({
    id: 'muni-fill', label: 'Municipalities coloured by people in flooded buildings', group: 'Impact', kind: 'fill', data: dataUrl('municipalities.geojson'), defaultOn: false,
    paint: { 'fill-color': ['interpolate', ['linear'], ['coalesce', ['get', 'people'], 0], 0, '#ffffff', 1000, '#fdd49e', 5000, '#fc8d59', 10000, '#d7301f'], 'fill-opacity': 0.55,
      'fill-outline-color': '#888888' },
    legend: [{ color: '#fdd49e', label: '1,000 people' }, { color: '#fc8d59', label: '5,000' }, { color: '#d7301f', label: '≥ 10,000' }],
    popup: (x) => <><Title>{String(x.municipality)}</Title>
      <Row k="Flooded buildings" v={`${n0(x.buildings)} (${Math.round(Number(x.share_buildings) * 100)} %)`} />
      <Row k="People in flooded buildings" v={n0(x.people)} /><Row k="Ground-level exposed" v={n0(x.people_ground)} />
      <Row k="Mean / max depth" v={`${x.mean_depth} / ${x.max_depth} m`} /><Row k="Loss (2010 €)" v={`${Number(x.loss_meur).toFixed(0)} M€`} /></>,
  }),
  roadsCut: (p: Palette): MapLayer => ({
    id: 'roads', label: 'Roads under ≥ 0.3 m of water', group: 'Impact', kind: 'line', data: dataUrl('roads_cut.geojson'), defaultOn: false,
    paint: { 'line-color': p['cat-2'], 'line-width': ['interpolate', ['linear'], ['zoom'], 9, 0.4, 15, 2.2] },
    legend: [{ color: p['cat-2'], label: 'road cut for ordinary vehicles', shape: 'line' }],
    popup: (x) => <><Title>Road ({String(x.class)})</Title><Row k="Max depth" v={`${x.depth} m`} /></>,
  }),
  facilities: (): MapLayer => ({
    id: 'fac', label: 'Flooded critical facilities', group: 'Impact', kind: 'circle', data: dataUrl('facilities_flooded.geojson'), defaultOn: false,
    paint: { 'circle-color': ['match', ['get', 'facility'], 'hospital', '#d62728', 'school', '#7a5cc4', 'fire_police', '#1f4fa8', '#e87ba4'], 'circle-radius': 5,
      'circle-stroke-color': '#ffffff', 'circle-stroke-width': 1.2 },
    legend: [{ color: '#d62728', label: 'hospital / health centre', shape: 'dot' }, { color: '#7a5cc4', label: 'school', shape: 'dot' },
      { color: '#1f4fa8', label: 'fire / police', shape: 'dot' }, { color: '#e87ba4', label: 'care home', shape: 'dot' }],
    popup: (x) => <><Title>{String(x.name ?? 'Facility')}</Title><Row k="Type" v={String(x.facility)} /><Row k="Modelled depth" v={`${x.depth} m`} /></>,
  }),
}

export const TIER_COLORS = ['#8c1c13', '#e66101', '#fdb863']

/** Priority cells coloured by tier (1 = highest), built from re-weighted data on the client. */
export function priorityLayer(data: object): MapLayer {
  return {
    id: 'prio', label: 'Priority cells (250 m), by tier', group: 'Priority', kind: 'fill', data, defaultOn: true,
    paint: { 'fill-color': ['match', ['get', 'tier'], 1, TIER_COLORS[0], 2, TIER_COLORS[1], TIER_COLORS[2]],
      'fill-opacity': ['match', ['get', 'tier'], 1, 0.85, 2, 0.6, 0.35] },
    legend: [{ color: TIER_COLORS[0], label: 'Tier 1: top 5 % of ranked cells' }, { color: TIER_COLORS[1], label: 'Tier 2: next 15 %' }, { color: TIER_COLORS[2], label: 'Tier 3: other affected cells' }],
    popup: (x) => <><Title>Rank {n0(x.rank)} · tier {String(x.tier)}</Title><Row k="Municipality" v={String(x.municipality ?? '–')} />
      <Row k="Priority score" v={Number(x.score).toFixed(1)} /><Row k="People exposed (ground)" v={n0(x.people)} /><Row k="Severity-weighted people" v={n0(x.people_sev)} />
      <Row k="Building loss (2010 €)" v={`${n0(x.loss_k)} k€`} /><Row k="Max depth" v={`${x.maxd} m`} /><Row k="Roads cut" v={`${Math.round(Number(x.road_cut) * 100)} %`} />
      {x.fac && <div className="mt-1 text-xs text-ink-2">Facilities: {String(x.fac)}</div>}</>,
  }
}
