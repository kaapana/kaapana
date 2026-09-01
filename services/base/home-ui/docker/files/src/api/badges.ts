import { httpClient } from '@kaapana/base-ui'

/**
 * Count behind a menu-badge path (the `kaapana.ai/ui.badge-path` an ingress
 * declares, e.g. kube-helm's pending-applications-count). Null on any failure
 * — callers keep the last known count, like the shell's menu badges do.
 */
export async function fetchBadgeCount(path: string): Promise<number | null> {
  try {
    const res = await httpClient.get<{ count: number }>(path)
    const count = res.data?.count
    return typeof count === 'number' ? count : null
  } catch {
    return null
  }
}
