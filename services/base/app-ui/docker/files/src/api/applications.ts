import { httpClient } from '@kaapana/base-ui'
import type { Pod } from '@/utils/podStatus'

interface RawActiveApplication {
  annotations: Record<string, string>
  created_at: string
  from_workflow_run: boolean
  name: string
  paths: string[]
  pods: Pod[]
  project: string | number
  release_name: string
}

export interface ActiveApplication {
  name: string
  releaseName: string
  createdAt: string
  startedAt: number | null
  fromWorkflowRun: boolean
  paths: string[]
  pods: Pod[]
  project: string | number
}

const TIMEOUT_MS = 10_000

const dateFormat = new Intl.DateTimeFormat('en-GB', { dateStyle: 'long', timeStyle: 'short' })

function toActiveApplication(raw: RawActiveApplication): ActiveApplication {
  const startedAt = new Date(raw.created_at).getTime()
  const hasStart = !Number.isNaN(startedAt)
  return {
    name: raw.annotations?.['kaapana.ai/display-name'] ?? raw.name ?? raw.release_name,
    releaseName: raw.release_name,
    createdAt: hasStart ? dateFormat.format(startedAt) : 'at an unknown time',
    startedAt: hasStart ? startedAt : null,
    fromWorkflowRun: raw.from_workflow_run,
    paths: raw.paths,
    pods: raw.pods ?? [],
    project: raw.project,
  }
}

export async function fetchActiveApplications(): Promise<ActiveApplication[]> {
  const { data } = await httpClient.get<RawActiveApplication[]>(
    '/kube-helm-api/active-applications',
    {
      timeout: TIMEOUT_MS,
    },
  )
  return data
    .filter((raw) => {
      if (raw.paths?.length) return true
      console.warn('Ignoring an application without paths:', raw)
      return false
    })
    .map(toActiveApplication)
}

/** Uninstalls the application and lets the workflow that started it continue. */
export async function completeActiveApplication(releaseName: string): Promise<void> {
  await httpClient.post(
    '/kube-helm-api/complete-active-application',
    { release_name: releaseName },
    { timeout: TIMEOUT_MS },
  )
}
