import { useEffect, useState } from 'react'
import type { Images } from './layers'

/* eslint-disable @typescript-eslint/no-explicit-any */
export type Summary = Record<string, any>

const base = import.meta.env.BASE_URL
const getJson = <T,>(name: string): Promise<T> =>
  fetch(`${base}data/${name}`).then((r) => {
    if (!r.ok) throw new Error(`${name}: ${r.status}`)
    return r.json() as Promise<T>
  })

export interface SiteData { summary: Summary; images: Images }

export function useSiteData(): { data?: SiteData; error?: string } {
  const [state, setState] = useState<{ data?: SiteData; error?: string }>({})
  useEffect(() => {
    Promise.all([getJson<Summary>('summary.json'), getJson<Images>('images.json')])
      .then(([summary, images]) => setState({ data: { summary, images } }))
      .catch((e) => setState({ error: String(e) }))
  }, [])
  return state
}

export const n0 = (v: number | undefined | null) => (v == null || Number.isNaN(v) ? '–' : Math.round(v).toLocaleString('en'))
export const n1 = (v: number | undefined | null) => (v == null || Number.isNaN(v) ? '–' : v.toLocaleString('en', { maximumFractionDigits: 1, minimumFractionDigits: 1 }))
export const pct = (v: number | undefined | null, d = 0) => (v == null || Number.isNaN(v) ? '–' : `${(v * 100).toFixed(d)} %`)
export const meur = (eur: number) => `${n0(eur / 1e6)} M€`
