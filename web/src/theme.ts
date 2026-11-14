import { useEffect, useState } from 'react'

const ROLES = [
  'surface', 'text-primary', 'text-secondary', 'text-muted', 'grid', 'axis', 'accent', 'neutral',
  'cat-1', 'cat-2', 'cat-3', 'cat-4', 'cat-5',
] as const

export type Palette = Record<(typeof ROLES)[number], string>

function readPalette(): Palette {
  const css = getComputedStyle(document.documentElement)
  return Object.fromEntries(ROLES.map((r) => [r, css.getPropertyValue(`--${r}`).trim()])) as Palette
}

const darkQuery = () => window.matchMedia('(prefers-color-scheme: dark)')

/** Resolved colour roles, re-read when the OS switches light/dark. */
export function usePalette(): { palette: Palette; dark: boolean } {
  const [state, setState] = useState(() => ({ palette: readPalette(), dark: darkQuery().matches }))
  useEffect(() => {
    const mq = darkQuery()
    const update = () => setState({ palette: readPalette(), dark: mq.matches })
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])
  return state
}

/** Sequential ramp for flood depth (m), light to dark blue; shared by the map legend and the raster. */
export const DEPTH_RAMP: { upTo: number; color: string; label: string }[] = [
  { upTo: 0.25, color: '#cfe8f7', label: '0.1 – 0.25 m' },
  { upTo: 0.5, color: '#9ccdee', label: '0.25 – 0.5 m' },
  { upTo: 1, color: '#5aa7de', label: '0.5 – 1 m' },
  { upTo: 2, color: '#2a78d6', label: '1 – 2 m' },
  { upTo: 4, color: '#1d4f9e', label: '2 – 4 m' },
  { upTo: 99, color: '#13294f', label: '> 4 m' },
]

/** Damage ratio classes (share of building value lost), one hue from light to dark. */
export const DAMAGE_RAMP: { upTo: number; color: string; label: string }[] = [
  { upTo: 0.1, color: '#ffe9a8', label: 'Minor  < 10 %' },
  { upTo: 0.3, color: '#fdb863', label: 'Moderate  10 – 30 %' },
  { upTo: 0.6, color: '#e66101', label: 'Major  30 – 60 %' },
  { upTo: 1.01, color: '#8c1c13', label: 'Severe  > 60 %' },
]
