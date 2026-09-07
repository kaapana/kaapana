import http from '@/api/http'
import type { MenuResponse } from '@/types/menu'

export async function fetchMenu(): Promise<MenuResponse> {
  const res = await http.get<MenuResponse>('/portal-api/menu')
  return res.data
}
