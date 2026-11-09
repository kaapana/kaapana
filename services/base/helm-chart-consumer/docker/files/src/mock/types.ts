// Shapes of the mock data. They follow the concept (services/base/helm-chart-consumer/concept.md),
// not an existing API: the Helm Chart Consumer API does not exist yet.

export type Role = 'scientist' | 'principal-investigator' | 'kaapana-system-admin'

/** The states of a deployed application (Story 3.1). */
export type AppState = 'DEPLOYING' | 'READY' | 'FAILED' | 'UPDATING' | 'UNDEPLOYING'

export type ParamType = 'string' | 'integer' | 'boolean' | 'choice'

export type ParamValue = string | number | boolean | null

/** A deploy parameter as declared in helm-chart-content.json (Story 2.2). */
export interface ParamDecl {
  key: string
  label: string
  type: ParamType
  description: string
  default: ParamValue
  required?: boolean
  min?: number
  max?: number
  minLength?: number
  unit?: string
  /** For `choice`; the special value 'project-folders' lists the project's bucket folders. */
  choices?: { title: string; value: string }[] | 'project-folders'
  /** Masked wherever the configuration is shown (Story 3.2). */
  secret?: boolean
  /** The chart value this parameter is mapped onto (Story 2.2). */
  chartValue: string
  /** Rendering of the value inside the chart values, e.g. a unit suffix. */
  chartSuffix?: string
}

export type Scope = 'project' | 'platform'

export interface Application {
  id: string
  name: string
  description: string
  icon: string
  multiDeployable: boolean
  scopes: readonly [Scope, ...Scope[]]
  versions: AppVersion[]
}

export interface AppVersion {
  version: string
  registered: boolean
  /** Path below the instance URL that the web interface serves (Story 4.4). */
  entryPath: string
  params: ParamDecl[]
  /** Key of the parameter that sizes the persistent workspace (Story 2.7), if any. */
  workspaceParam?: string
  /** Key of the parameter that picks the project data folder (Story 2.5), if any. */
  dataFolderParam?: string
}

export interface Person {
  id: string
  name: string
}

export interface Persona extends Person {
  /** Role per project short id. kaapana-system-admins have no entry: they may act everywhere. */
  roles: Record<string, Role>
  admin: boolean
  summary: string
}

export interface Project {
  id: string
  name: string
  bucket: string
  folders: string[]
  /** Person ids with their role in the project. */
  members: Record<string, Role>
}

export interface Pod {
  name: string
  status: string
  ready: string
  restarts: number
  startedAt: number
}

export interface K8sEvent {
  type: 'Normal' | 'Warning'
  reason: string
  object: string
  message: string
  at: number
}

export type AppScope =
  | {
      kind: 'project'
      projectId: string
      /**
       * This is the member the instance was deployed for, or null if it was deployed for the whole
       * project. It does not limit who can open the instance.
       */
      forPerson: string | null
    }
  | { kind: 'platform' }

export interface DeployedApp {
  id: string
  /**
   * The details page finds an instance by its name. The name is therefore unique among the
   * applications listed in a project, including the platform-wide ones.
   */
  name: string
  appId: string
  version: string
  scope: AppScope
  description: string
  deployedBy: string
  deployedAt: number
  values: Record<string, ParamValue>
  state: AppState
  pods: Pod[]
  events: K8sEvent[]
  /** Why the application is FAILED, in words a scientist understands (Story 3.1). */
  failure?: { reason: string; helm: string }
  /**
   * Reconciliation with the helm releases in the cluster (Story 12.1):
   * 'changed' — the release was upgraded outside Kaapana, 'removed' — it no longer exists.
   */
  drift?: {
    kind: 'changed' | 'removed'
    detectedAt: number
    revision?: number
    recordedRevision?: number
  }
}

export interface ShellNotification {
  id: string
  type: 'success' | 'error' | 'info'
  title: string
  text: string
  at: number
  read: boolean
}
