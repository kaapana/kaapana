import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { notify } from '@kyvg/vue3-notification'
import type { ApiErrorInfo } from '@kaapana/base-ui'
import {
  applications,
  MOCK_HOST,
  otherPeople,
  personas,
  seedAvailability,
  seedDeployed,
  seedProjects,
} from '@/mock/data'
import type {
  Application,
  AppScope,
  AppVersion,
  DeployedApp,
  ParamValue,
  Pod,
  Project,
  Role,
  Scope,
  ShellNotification,
} from '@/mock/types'

// The whole mock lives in this store: no request leaves the browser and a reload
// starts from the seed data again. Timers stand in for the cluster: they move a
// deployment through its states the way the Helm Chart Consumer would report them.

export type PendingLeave =
  { kind: 'route'; to: string } | { kind: 'project'; id: string } | { kind: 'persona'; id: string }

export interface DryRunResult {
  ok: boolean
  message: string
  error?: ApiErrorInfo
}

export type VersionStatus =
  | { kind: 'newest' }
  | { kind: 'newer-registered'; newest: string }
  | { kind: 'deregistered'; newest: string | null }

export interface ScopeOption {
  scope: Scope
  blockedBy: DeployedApp | null
}

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value))
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
// newId() only exists in secure contexts; the mock may be served over plain http.
const newId = () => Math.random().toString(36).slice(2) + Date.now().toString(36)

function compareVersions(a: string, b: string): number {
  const pa = a.split('.').map(Number)
  const pb = b.split('.').map(Number)
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const diff = (pa[i] ?? 0) - (pb[i] ?? 0)
    if (diff) return diff
  }
  return 0
}

export const roleLabels: Record<Role, string> = {
  scientist: 'Scientist',
  'principal-investigator': 'Principal investigator',
  'kaapana-system-admin': 'Kaapana system admin',
}

export const useMockStore = defineStore('mock', () => {
  const personaId = ref('paul')
  const projectId = ref('lung-ct')
  const showStoryRefs = ref(false)
  const storyPanel = ref(false)
  const dark = ref(false)
  const highlightStory = ref<string | null>(null)

  const projects = ref<Project[]>(clone(seedProjects))
  const deployed = ref<DeployedApp[]>(seedDeployed(Date.now()))
  const availability = ref<Record<string, string[]>>(clone(seedAvailability))
  const notifications = ref<ShellNotification[]>([])
  const restarting = ref(false)
  const reconciledAt = ref(Date.now() - 2 * 60_000)

  // Shell state: the view reports unsaved changes, the shell asks before leaving.
  const dirty = ref(false)
  const pendingLeave = ref<PendingLeave | null>(null)
  const openedAppId = ref<string | null>(null)

  // Timers of the previous mock run must not touch the data after a reset.
  let generation = 0

  const persona = computed(() => personas.find((p) => p.id === personaId.value)!)
  const project = computed(() => projects.value.find((p) => p.id === projectId.value)!)

  const accessibleProjects = computed(() =>
    persona.value.admin
      ? projects.value
      : projects.value.filter((p) => persona.value.id in p.members),
  )

  const role = computed<Role | null>(() => {
    if (persona.value.admin) return 'kaapana-system-admin'
    return project.value?.members[persona.value.id] ?? null
  })

  const can = computed(() => {
    const admin = role.value === 'kaapana-system-admin'
    const pi = role.value === 'principal-investigator'
    const deploy: Record<Scope, boolean> = { project: pi || admin, platform: admin }
    const undeploy: Record<Scope, boolean> = { project: pi || admin, platform: admin }
    return {
      deploy,
      undeploy,
      catalog: deploy.project || deploy.platform,
      manageAvailability: admin,
      manageProjects: admin,
    }
  })

  function canOpen(scope: AppScope): boolean {
    return (
      scope.kind === 'platform' ||
      persona.value.admin ||
      persona.value.id in (projects.value.find((p) => p.id === scope.projectId)?.members ?? {})
    )
  }

  function projectAppsOf(id: string): DeployedApp[] {
    return deployed.value.filter((d) => d.scope.kind === 'project' && d.scope.projectId === id)
  }

  function liveInstances(appId: string, where: { projectId: string } | 'platform'): DeployedApp[] {
    const pool =
      where === 'platform'
        ? deployed.value.filter((d) => d.scope.kind === 'platform')
        : projectAppsOf(where.projectId)
    return pool.filter((d) => d.appId === appId && d.state !== 'UNDEPLOYING')
  }

  const listedApps = computed(() =>
    deployed.value.filter(
      (d) => d.scope.kind === 'platform' || d.scope.projectId === projectId.value,
    ),
  )

  const unreadCount = computed(() => notifications.value.filter((n) => !n.read).length)

  function application(appId: string): Application {
    return applications.find((a) => a.id === appId)!
  }

  function versionOf(app: Pick<DeployedApp, 'appId' | 'version'>): AppVersion {
    return application(app.appId).versions.find((v) => v.version === app.version)!
  }

  function registeredVersions(appId: string): AppVersion[] {
    return application(appId)
      .versions.filter((v) => v.registered)
      .sort((a, b) => compareVersions(b.version, a.version))
  }

  function newestRegisteredVersion(appId: string): AppVersion | undefined {
    return registeredVersions(appId)[0]
  }

  function versionStatus(app: DeployedApp): VersionStatus {
    const newest = newestRegisteredVersion(app.appId)?.version ?? null
    if (!versionOf(app).registered) return { kind: 'deregistered', newest }
    if (newest !== null && compareVersions(newest, app.version) > 0)
      return { kind: 'newer-registered', newest }
    return { kind: 'newest' }
  }

  function isEnabled(project: string, appId: string): boolean {
    return availability.value[project]?.includes(appId) ?? false
  }

  function deployOptions(appId: string): ScopeOption[] {
    const app = application(appId)
    const options: ScopeOption[] = []
    if (
      app.scopes.includes('project') &&
      can.value.deploy.project &&
      isEnabled(projectId.value, appId)
    ) {
      const blockedBy = app.multiDeployable
        ? null
        : (liveInstances(appId, { projectId: projectId.value })[0] ?? null)
      options.push({ scope: 'project', blockedBy })
    }
    if (app.scopes.includes('platform') && can.value.deploy.platform) {
      options.push({ scope: 'platform', blockedBy: liveInstances(appId, 'platform')[0] ?? null })
    }
    return options
  }

  function blockingInstance(appId: string): DeployedApp | null {
    const options = deployOptions(appId)
    return options.length > 0 && options.every((o) => o.blockedBy) ? options[0].blockedBy : null
  }

  function singleInstanceNotice(instance: DeployedApp): { title: string; text: string } {
    const once = instance.scope.kind === 'platform' ? 'platform-wide' : 'per project'
    return {
      title: `${application(instance.appId).name} is already deployed ${scopePhrase(instance.scope)}`,
      text: `It can be deployed once ${once}. The existing instance is ${instance.name}.`,
    }
  }

  const catalog = computed(() =>
    applications.filter(
      (a) => registeredVersions(a.id).length > 0 && deployOptions(a.id).length > 0,
    ),
  )

  function personName(id: string | null): string {
    if (!id) return ''
    return [...personas, ...otherPeople].find((p) => p.id === id)?.name ?? id
  }

  function projectName(id: string): string {
    return projects.value.find((p) => p.id === id)?.name ?? id
  }

  function scopePhrase(scope: AppScope): string {
    return scope.kind === 'project' ? `in ${projectName(scope.projectId)}` : 'platform-wide'
  }

  function instanceUrl(app: Pick<DeployedApp, 'scope' | 'name' | 'appId' | 'version'>): string {
    const base =
      app.scope.kind === 'project' ? `${MOCK_HOST}/project/${app.scope.projectId}` : MOCK_HOST
    return `${base}/applications/${app.name}/${versionOf(app).entryPath}`
  }

  function findByName(name: string): DeployedApp | undefined {
    return listedApps.value.find((d) => d.name === name)
  }

  function nameTaken(name: string, scope: Scope): boolean {
    return (scope === 'platform' ? deployed.value : listedApps.value).some((d) => d.name === name)
  }

  function suggestName(appId: string, scope: Scope): string {
    for (let n = 1; ; n++) {
      const candidate = `${appId}-${n}`
      if (!nameTaken(candidate, scope)) return candidate
    }
  }

  // ---- shell -------------------------------------------------------------

  function switchProject(id: string) {
    if (id === projectId.value) return
    if (dirty.value) {
      pendingLeave.value = { kind: 'project', id }
      return
    }
    projectId.value = id
  }

  function switchPersona(id: string) {
    if (id === personaId.value) return
    if (dirty.value) {
      pendingLeave.value = { kind: 'persona', id }
      return
    }
    applyPersona(id)
  }

  function applyPersona(id: string) {
    personaId.value = id
    if (!accessibleProjects.value.some((p) => p.id === projectId.value)) {
      projectId.value = accessibleProjects.value[0]?.id ?? projectId.value
    }
  }

  function addNotification(n: Omit<ShellNotification, 'id' | 'at' | 'read'>) {
    notifications.value.unshift({ ...n, id: newId(), at: Date.now(), read: false })
    // The shell shows a transient notification when a persistent one arrives.
    notify({ type: n.type === 'error' ? 'error' : n.type, title: n.title, text: n.text })
  }

  // ---- Helm Chart Consumer, simulated -----------------------------------

  /** Story 2.1 / 2.2 — the dry-run that precedes every deploy. */
  async function dryRun(
    appId: string,
    version: string,
    values: Record<string, ParamValue>,
  ): Promise<DryRunResult> {
    await wait(1200)
    const memory = Number(values.memory ?? 0)
    if (values.gpu === true && memory > 32) {
      const detail =
        `Error: INSTALLATION FAILED: values don't meet the specifications of the schema(s) in the following chart(s):\n` +
        `${appId}:\n- resources.limits.memory: Must be at most 32 when resources.gpu.enabled is true, ${memory} is set`
      return {
        ok: false,
        message: `The chart rejects this configuration: GPU nodes allow at most 32 GiB memory, and ${memory} GiB is set. Lower the memory or turn off the GPU.`,
        // A dry-run reports its problems in a successful response, so there is no failed
        // request to show. The details therefore show only the output of helm.
        error: {
          status: null,
          statusText: null,
          method: null,
          url: null,
          detail,
          requestId: null,
          message: null,
        },
      }
    }
    return {
      ok: true,
      message: `Dry run passed: helm can install ${application(appId).name} ${version} with this configuration.`,
    }
  }

  function deploy(input: {
    appId: string
    version: string
    scope: AppScope
    name: string
    description: string
    values: Record<string, ParamValue>
  }): DeployedApp {
    const now = Date.now()
    const podName = `${input.name}-${input.appId}-${Math.random().toString(36).slice(2, 11)}`
    const pod = (status: string, ready: string): Pod => ({
      name: podName,
      status,
      ready,
      restarts: 0,
      startedAt: now,
    })
    const app: DeployedApp = {
      id: newId(),
      name: input.name,
      appId: input.appId,
      version: input.version,
      scope: input.scope,
      description: input.description,
      deployedBy: personaId.value,
      deployedAt: now,
      values: { ...input.values },
      state: 'DEPLOYING',
      pods: [pod('Pending', '0/1')],
      events: [
        {
          type: 'Normal',
          reason: 'Scheduled',
          object: `pod/${podName}`,
          message: `Successfully assigned ${podName} to node worker-1`,
          at: now,
        },
      ],
    }
    deployed.value.push(app)
    const gen = generation
    const update = (fn: (d: DeployedApp) => void) => {
      if (gen !== generation) return
      const target = deployed.value.find((d) => d.id === app.id)
      if (target && target.state === 'DEPLOYING') fn(target)
    }
    setTimeout(() => update((d) => (d.pods = [pod('ContainerCreating', '0/1')])), 1500)
    setTimeout(() => update((d) => (d.pods = [pod('Running', '0/1')])), 4000)
    setTimeout(
      () =>
        update((d) => {
          d.pods = [pod('Running', '1/1')]
          d.state = 'READY'
          addNotification({
            type: 'success',
            title: 'Application ready',
            text: `${d.name} is ready to open ${scopePhrase(d.scope)}.`,
          })
        }),
      7000,
    )
    return app
  }

  function undeploy(id: string) {
    const app = deployed.value.find((d) => d.id === id)
    if (!app) return
    app.state = 'UNDEPLOYING'
    app.pods = app.pods.map((p) => ({ ...p, status: 'Terminating' }))
    const gen = generation
    setTimeout(() => {
      if (gen !== generation) return
      deployed.value = deployed.value.filter((d) => d.id !== id)
      const volume = versionOf(app).workspaceParam ? ' Its workspace volume was deleted.' : ''
      notify({
        type: 'success',
        title: 'Application undeployed',
        text: `${app.name} was undeployed ${scopePhrase(app.scope)}.${volume}`,
      })
    }, 2500)
  }

  /** Story 12.1 — drop an entry whose helm release was removed outside Kaapana. */
  function removeFromList(id: string) {
    const app = deployed.value.find((d) => d.id === id)
    deployed.value = deployed.value.filter((d) => d.id !== id)
    if (app)
      notify({
        type: 'success',
        title: 'Removed from the list',
        text: `${app.name} is no longer listed ${scopePhrase(app.scope)}.`,
      })
  }

  /** Story 5.2. */
  function setEnabled(project: string, appId: string, enabled: boolean) {
    const current = new Set(availability.value[project] ?? [])
    if (enabled) current.add(appId)
    else current.delete(appId)
    availability.value[project] = [...current]
    const running = liveInstances(appId, { projectId: project }).length
    const keep =
      !enabled && running
        ? ` ${running} deployed ${running === 1 ? 'instance keeps' : 'instances keep'} running.`
        : ''
    notify({
      type: 'success',
      title: enabled ? 'Application enabled' : 'Application disabled',
      text: `${application(appId).name} ${enabled ? 'can now be' : 'can no longer be'} deployed in ${projectName(project)}.${keep}`,
    })
  }

  function deleteProject(id: string): DeployedApp[] {
    const blocking = projectAppsOf(id)
    if (blocking.length > 0) return blocking
    const name = projectName(id)
    projects.value = projects.value.filter((p) => p.id !== id)
    delete availability.value[id]
    if (projectId.value === id) projectId.value = accessibleProjects.value[0]?.id ?? ''
    notify({ type: 'success', title: 'Project deleted', text: `${name} was deleted.` })
    return []
  }

  /** Story 12.1 — the list reloads and is reconciled with the helm releases. */
  async function simulateRestart() {
    if (restarting.value) return
    restarting.value = true
    const gen = generation
    await wait(3000)
    if (gen !== generation) return
    restarting.value = false
    reconciledAt.value = Date.now()
  }

  function openApp(app: DeployedApp) {
    openedAppId.value = app.id
  }

  function reset() {
    generation++
    projects.value = clone(seedProjects)
    deployed.value = seedDeployed(Date.now())
    availability.value = clone(seedAvailability)
    notifications.value = []
    restarting.value = false
    reconciledAt.value = Date.now() - 2 * 60_000
    dirty.value = false
    pendingLeave.value = null
    openedAppId.value = null
    projectId.value = accessibleProjects.value.some((p) => p.id === 'lung-ct')
      ? 'lung-ct'
      : (accessibleProjects.value[0]?.id ?? 'lung-ct')
    notify({
      type: 'info',
      title: 'Mock reset',
      text: 'All mock data is back to its initial state.',
    })
  }

  return {
    personaId,
    projectId,
    showStoryRefs,
    storyPanel,
    dark,
    highlightStory,
    projects,
    deployed,
    availability,
    notifications,
    restarting,
    reconciledAt,
    dirty,
    pendingLeave,
    openedAppId,
    persona,
    project,
    accessibleProjects,
    role,
    can,
    canOpen,
    projectAppsOf,
    liveInstances,
    listedApps,
    catalog,
    unreadCount,
    application,
    versionOf,
    registeredVersions,
    newestRegisteredVersion,
    versionStatus,
    isEnabled,
    deployOptions,
    blockingInstance,
    singleInstanceNotice,
    personName,
    projectName,
    scopePhrase,
    instanceUrl,
    findByName,
    nameTaken,
    suggestName,
    switchProject,
    switchPersona,
    applyPersona,
    addNotification,
    dryRun,
    deploy,
    undeploy,
    removeFromList,
    setEnabled,
    deleteProject,
    simulateRestart,
    openApp,
    reset,
  }
})
