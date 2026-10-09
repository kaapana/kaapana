const relative = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })

const MINUTE = 60
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

export function parseTimestamp(value: string | null | undefined): Date | null {
  if (!value) return null
  const date = new Date(value)
  if (isNaN(date.getTime()) || date.getUTCFullYear() < 1970) return null
  return date
}

export function formatTimestamp(value: string | null | undefined): string {
  const date = parseTimestamp(value)
  return date ? date.toLocaleString() : 'Never'
}

export function formatRelative(date: Date, now = Date.now()): string {
  const seconds = Math.round((date.getTime() - now) / 1000)
  const abs = Math.abs(seconds)
  if (abs < MINUTE) return relative.format(0, 'second')
  if (abs < HOUR) return relative.format(Math.round(seconds / MINUTE), 'minute')
  if (abs < DAY) return relative.format(Math.round(seconds / HOUR), 'hour')
  return relative.format(Math.round(seconds / DAY), 'day')
}

export interface Freshness {
  color: 'success' | 'warning' | 'error' | undefined
  label: string
}

export function freshness(timeUpdated: string | null | undefined, now = Date.now()): Freshness {
  const date = parseTimestamp(timeUpdated)
  if (!date) return { color: undefined, label: 'Never updated' }
  const age = (now - date.getTime()) / 1000
  const label = `Updated ${formatRelative(date, now)}`
  if (age < 5 * MINUTE) return { color: 'success', label }
  if (age < 5 * HOUR) return { color: 'warning', label }
  return { color: 'error', label }
}
