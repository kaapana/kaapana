import { httpClient } from '@kaapana/base-ui'
import type { Dataset } from '@/types/schemas'

export async function fetchDatasets(): Promise<Dataset[]> {
  const response = await httpClient.get<Dataset[]>('/kaapana-backend/client/datasets')
  return Array.isArray(response.data) ? response.data : []
}
