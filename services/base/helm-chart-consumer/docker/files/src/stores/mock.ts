import { computed, reactive, ref } from 'vue'
import { defineStore } from 'pinia'
import { notify } from '@kyvg/vue3-notification'
import type { ApiErrorInfo } from '@kaapana/base-ui'
import {
  appDefinitions,
  MOCK_HOST,
  otherPeople,
  personas,
  seedAvailability,
  seedDeployed,
  seedProjects,
} from '@/mock/data'
import type {
  AppDefinition,
  DeployedApp,
  ParamValue,
  Pod,
  Project,
  Role,
  ShellNotification,
} from '@/mock/types'

// The whole mock lives in this store: no request leaves the browser and a reload
// starts from the seed data again. Timers stand in for the cluster: they move a
// deployment through its states the way the Helm Chart Consumer would report them.

export type PendingLeave =
  { kind: 'route'; to: string } | { kind: 'project'; id: string } | { kind: 'persona'; id: string }

export type AppWindow =
  { kind: 'app'; id: string } | { kind: 'denied'; projectId: string; name: string }

export interface ConceptOptions {
  /** Q5 — what happens to persistent volumes on undeploy. */
  volumesOnUndeploy: 'ask' | 'delete' | 'keep'
  /** Q8 — whether a newly registered application starts enabled. */
  newAppDefault: 'disabled' | 'enabled'
  /** Q9 — deleting a project that still has deployed applications. */
  projectDeletion: 'undeploy' | 'refuse'
}

export interface DryRunResult {
  ok: boolean
  message: string
  error?: ApiErrorInfo
}

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value))
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
// newId() only exists in secure contexts; the mock may be served over plain http.
const newId = () => Math.random().toString(36).slice(2) + Date.now().toString(36)

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
  const options = reactive<ConceptOptions>({
    volumesOnUndeploy: 'ask',
    newAppDefault: 'disabled',
    projectDeletion: 'undeploy',
  })

  const projects = ref<Project[]>(clone(seedProjects))
  const deployed = ref<DeployedApp[]>(seedDeployed(Date.now()))
  const availability = ref<Record<string, string[]>>(clone(seedAvailability))
  const notifications = ref<ShellNotification[]>([])
  const restarting = ref(false)
  const reconciledAt = ref(Date.now() - 2 * 60_000)

  // Shell state: the view reports unsaved changes, the shell asks before leaving.
  const dirty = ref(false)
  const pendingLeave = ref<PendingLeave | null>(null)
  const appWindow = ref<AppWindow | null>(null)

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

  // Story 5.1 — the default mapping of roles to actions.
  const can = computed(() => ({
    deploy: role.value === 'principal-investigator' || role.value === 'kaapana-system-admin',
    undeploy: role.value === 'principal-investigator' || role.value === 'kaapana-system-admin',
    open: role.value !== null,
    manageAvailability: role.value === 'kaapana-system-admin',
    manageProjects: role.value === 'kaapana-system-admin',
  }))

  const projectApps = computed(() => deployed.value.filter((d) => d.projectId === projectId.value))

  const enabledApps = computed(() =>
    appDefinitions.filter((a) => availability.value[projectId.value]?.includes(a.id)),
  )

  const unreadCount = computed(() => notifications.value.filter((n) => !n.read).length)

  function definition(appId: string): AppDefinition {
    return appDefinitions.find((a) => a.id === appId)!
  }

  function personName(id: string | null): string {
    if (!id) return ''
    return [...personas, ...otherPeople].find((p) => p.id === id)?.name ?? id
  }

  function projectName(id: string): string {
    return projects.value.find((p) => p.id === id)?.name ?? id
  }

  function instanceUrl(app: Pick<DeployedApp, 'projectId' | 'name' | 'appId'>): string {
    const entry = definition(app.appId).entryPath
    return `${MOCK_HOST}/project/${app.projectId}/applications/${app.name}/${entry}`
  }

  function findByName(name: string): DeployedApp | undefined {
    return projectApps.value.find((d) => d.name === name)
  }

  function nameTaken(name: string): boolean {
    return projectApps.value.some((d) => d.name === name)
  }

  function suggestName(appId: string): string {
    for (let n = 1; ; n++) {
      const candidate = `${appId}-${n}`
      if (!nameTaken(candidate)) return candidate
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
  async function dryRun(appId: string, values: Record<string, ParamValue>): Promise<DryRunResult> {
    await wait(1200)
    const memory = Number(values.memory ?? 0)
    if (values.gpu === true && memory > 32) {
      const detail =
        `Error: INSTALLATION FAILED: admission webhook "resources.kaapana.ai" denied the request: ` +
        `pods requesting nvidia.com/gpu may request at most 32Gi memory, requested ${memory}Gi`
      return {
        ok: false,
        message: `The chart rejects this configuration: GPU nodes allow at most 32 GiB memory, and ${memory} GiB is set. Lower the memory or turn off the GPU.`,
        error: {
          status: 422,
          statusText: 'Unprocessable Entity',
          method: 'POST',
          url: `/helm-chart-consumer/v1/projects/${projectId.value}/applications/dry-run`,
          detail,
          requestId: 'mock-' + Math.random().toString(16).slice(2, 10),
          message: 'Request failed with status code 422',
        },
      }
    }
    return {
      ok: true,
      message: `Dry run passed: helm can install ${definition(appId).name} with this configuration.`,
    }
  }

  function deploy(input: {
    appId: string
    name: string
    description: string
    forPerson: string | null
    values: Record<string, ParamValue>
  }): DeployedApp {
    const def = definition(input.appId)
    const now = Date.now()
    const podName = `${input.name}-${def.id}-${Math.random().toString(36).slice(2, 11)}`
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
      appId: def.id,
      version: def.version,
      projectId: projectId.value,
      description: input.description,
      forPerson: input.forPerson,
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
          message: `Successfully assigned ${projectId.value}/${podName} to node worker-1`,
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
            text: `${d.name} in ${projectName(d.projectId)} is ready to open.`,
          })
        }),
      7000,
    )
    return app
  }

  /** Story 2.3. `deleteVolume` follows Q5 (concept options). */
  function undeploy(id: string, deleteVolume: boolean) {
    const app = deployed.value.find((d) => d.id === id)
    if (!app) return
    app.state = 'UNDEPLOYING'
    app.pods = app.pods.map((p) => ({ ...p, status: 'Terminating' }))
    const gen = generation
    setTimeout(() => {
      if (gen !== generation) return
      deployed.value = deployed.value.filter((d) => d.id !== id)
      const def = definition(app.appId)
      const volume = def.workspaceParam
        ? deleteVolume
          ? ' Its volume was deleted.'
          : ' Its volume was kept.'
        : ''
      notify({
        type: 'success',
        title: 'Application undeployed',
        text: `${app.name} was removed from ${projectName(app.projectId)}.${volume}`,
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
        text: `${app.name} no longer appears in ${projectName(app.projectId)}.`,
      })
  }

  /** Story 5.2. */
  function setEnabled(project: string, appId: string, enabled: boolean) {
    const current = new Set(availability.value[project] ?? [])
    if (enabled) current.add(appId)
    else current.delete(appId)
    availability.value[project] = [...current]
    const running = deployed.value.filter(
      (d) => d.projectId === project && d.appId === appId,
    ).length
    const keep =
      !enabled && running
        ? ` ${running} deployed ${running === 1 ? 'instance keeps' : 'instances keep'} running.`
        : ''
    notify({
      type: 'success',
      title: enabled ? 'Application enabled' : 'Application disabled',
      text: `${definition(appId).name} ${enabled ? 'can now be' : 'can no longer be'} deployed in ${projectName(project)}.${keep}`,
    })
  }

  /** Story 12.2 — only called when Q9 allows the deletion. */
  function deleteProject(id: string) {
    const name = projectName(id)
    const removed = deployed.value.filter((d) => d.projectId === id).length
    deployed.value = deployed.value.filter((d) => d.projectId !== id)
    projects.value = projects.value.filter((p) => p.id !== id)
    delete availability.value[id]
    if (projectId.value === id) projectId.value = accessibleProjects.value[0]?.id ?? ''
    notify({
      type: 'success',
      title: 'Project deleted',
      text: removed
        ? `${name} was deleted. ${removed} ${removed === 1 ? 'application was' : 'applications were'} undeployed.`
        : `${name} was deleted.`,
    })
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
    appWindow.value = { kind: 'app', id: app.id }
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
    appWindow.value = null
    Object.assign(options, {
      volumesOnUndeploy: 'ask',
      newAppDefault: 'disabled',
      projectDeletion: 'undeploy',
    })
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
    options,
    projects,
    deployed,
    availability,
    notifications,
    restarting,
    reconciledAt,
    dirty,
    pendingLeave,
    appWindow,
    persona,
    project,
    accessibleProjects,
    role,
    can,
    projectApps,
    enabledApps,
    unreadCount,
    definition,
    personName,
    projectName,
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
