import http from '@/api/http'
import type { MenuResponse } from '@/types/menu'

export async function fetchMenu(fresh = false): Promise<MenuResponse> {
  const res = await http.get<MenuResponse>(`/portal-api/menu${fresh ? '?fresh=1' : ''}`)
  return res.data
}
