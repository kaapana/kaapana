import { httpClient } from '@kaapana/base-ui'

const KAAPANA_BACKEND_ENDPOINT = import.meta.env.VITE_APP_KAAPANA_BACKEND_ENDPOINT

export interface DashboardData {
  metrics: Record<string, number | string>
  histograms: Record<string, { items: Record<string, number> }>
}

/**
 * Patient/study/series counts + histograms for the selected project. Scoping is
 * server-side: auth-backend derives the OpenSearch index from the
 * /project/<short_id> prefix the base-ui httpClient adds.
 */
export async function loadDashboard(
  names: string[],
  query: Record<string, unknown> = {},
): Promise<DashboardData> {
  const res = await httpClient.post<DashboardData>(`${KAAPANA_BACKEND_ENDPOINT}dataset/dashboard`, {
    series_instance_uids: [],
    names,
    query,
  })
  return res.data
}

/**
 * The same counts for a project other than the one in the document URL: the
 * /project/<slug> prefix is written out by hand since the httpClient leaves an
 * already-prefixed path untouched. `names` stays empty on purpose — every name
 * adds a terms aggregation over the whole index, and this runs once per project.
 */
export async function loadProjectDashboard(slug: string): Promise<DashboardData> {
  const res = await httpClient.post<DashboardData>(
    `/project/${slug}${KAAPANA_BACKEND_ENDPOINT}dataset/dashboard`,
    { series_instance_uids: [], names: [], query: {} },
  )
  return res.data
}
