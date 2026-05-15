import axios from 'axios'

export function getApiErrorMessage(err: unknown, fallbackMessage: string): string {
  if (!axios.isAxiosError(err)) return fallbackMessage

  const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail

  return typeof detail === 'string' ? detail : fallbackMessage
}
