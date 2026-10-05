export interface Pod {
  name: string
  status: string
  ready: string
  restarts: number | string
}

export type PodStatus = 'ready' | 'pending' | 'error'

const TRANSIENT_STATES = ['pending', 'containercreating', 'podinitializing', 'terminating']

function isPodHealthy(pod: Pod): boolean {
  const status = (pod.status || '').toLowerCase()
  const [readyCount, wantCount] = (pod.ready || '').split('/')
  return status === 'completed' || (status === 'running' && readyCount === wantCount)
}

// Init:0/2 is progress, while Init:Error and Init:OOMKilled are failures.
function isPodStarting(pod: Pod): boolean {
  const status = (pod.status || '').toLowerCase()
  return status === 'running' || /^init:\d/.test(status) || TRANSIENT_STATES.includes(status)
}

/** Classifies an application by the Kubernetes status of its pods. */
export function podStatus(pods: Pod[] | undefined): PodStatus {
  const unhealthy = (pods ?? []).filter((pod) => !isPodHealthy(pod))
  if (!pods?.length) return 'pending'
  if (unhealthy.some((pod) => !isPodStarting(pod))) return 'error'
  if (unhealthy.length) return 'pending'
  return 'ready'
}

export function problemPods(pods: Pod[] | undefined): Pod[] {
  return (pods ?? []).filter((pod) => !isPodHealthy(pod))
}

export function describePod(pod: Pod): string {
  return `${pod.name}: ${pod.status} (${pod.ready}, restarts: ${pod.restarts})`
}
