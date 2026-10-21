export const EXTENSIONS_API = '/extensions-api'

export function asList<T>(data: unknown): T[] {
  return Array.isArray(data) ? (data as T[]) : []
}
