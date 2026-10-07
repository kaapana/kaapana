<template>
  <v-container fluid class="text-left runs-view">
    <div class="d-flex flex-wrap align-start justify-space-between ga-4 mb-4">
      <div>
        <h1 class="text-h4">Workflow runs</h1>
        <p class="text-body-2 text-medium-emphasis mt-1">
          Follow, cancel, retry and delete the workflow runs of this project.
          <template v-if="polling">The list updates automatically while runs are active.</template>
        </p>
      </div>

      <div class="d-flex flex-wrap align-center ga-2">
        <v-btn
          color="error"
          variant="tonal"
          prepend-icon="mdi-broom"
          :disabled="eligibleForCleanup.length === 0 || cleanupRunning"
          :loading="cleanupRunning"
          @click="askBulkCleanup"
        >
          Clean finished runs
        </v-btn>
        <v-btn
          :prepend-icon="kaapanaIcons.refresh"
          :loading="refreshing"
          :disabled="loading"
          @click="loadRuns()"
        >
          Refresh
        </v-btn>
      </div>
    </div>

    <SearchBar
      v-model:filters="appliedFilters"
      v-model:text="searchText"
      v-model:sort="sort"
      :runs="runs"
      class="mb-4"
    />

    <div
      v-if="runs.length"
      class="d-flex flex-wrap align-center ga-2 mb-4"
      data-testid="status-summary"
    >
      <span class="text-body-2">
        {{ runs.length }} {{ runs.length === 1 ? 'run' : 'runs' }}
        <span v-if="visibleRuns.length !== runs.length" class="text-medium-emphasis">
          ({{ visibleRuns.length }} shown)
        </span>
      </span>
      <v-chip
        v-for="(count, status) in statusStatistics"
        :key="status"
        size="small"
        :color="statusColor(status)"
        :variant="isStatusFiltered(status) ? 'flat' : 'outlined'"
        :aria-pressed="isStatusFiltered(status)"
        :aria-label="`${status}: ${count}. ${isStatusFiltered(status) ? 'Remove' : 'Add'} status filter`"
        @click="toggleStatusFilter(status)"
      >
        {{ status }} · {{ count }}
      </v-chip>
    </div>

    <CollectionState
      v-if="loadError"
      state="error"
      noun="workflow runs"
      empty-text=""
      error-text="The workflow service could not be reached or reported an error. Try again, or contact your administrator if it persists."
      has-error-details
      :retrying="loading"
      @retry="loadRuns()"
      @show-details="showLoadErrorDetails"
    />

    <v-card v-else :elevation="2">
      <v-data-table
        :headers="tableHeaders"
        :items="visibleRuns"
        :loading="loading"
        loading-text="Loading workflow runs…"
        :items-per-page="25"
        :items-per-page-options="[10, 25, 50, 100]"
        density="comfortable"
      >
        <template #item="{ item }">
          <WorkflowRunRow
            :run="item"
            :busy="busyRuns[item.id] ?? null"
            @cancel="askCancel"
            @retry="retryRun"
            @clean="askCleanup"
            @delete="askDelete"
            @view-logs="viewLogs"
          />
        </template>
        <template #no-data>
          <CollectionState
            :state="runs.length ? 'no-matches' : 'empty'"
            noun="workflow runs"
            empty-text="Start a workflow to see its run here."
            @clear-filters="clearFilters"
          >
            <template #empty-actions>
              <v-btn color="primary" variant="text" @click="navigateShell(WORKFLOWS_SHELL_ROUTE)">
                Open workflows
              </v-btn>
            </template>
          </CollectionState>
        </template>
      </v-data-table>
    </v-card>

    <ConfirmDialog
      v-model="confirmOpen"
      :title="confirmContent.title"
      :text="confirmContent.text"
      :confirm-text="confirmContent.confirmText"
      :cancel-text="confirmContent.cancelText"
      color="error"
      @confirm="executeConfirmed"
    />
  </v-container>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  apiErrorInfo,
  ConfirmDialog,
  kaapanaIcons,
  navigateShell,
  type ApiErrorInfo,
} from '@kaapana/base-ui'
import CollectionState from '@/components/CollectionState.vue'
import SearchBar from '@/components/SearchBar.vue'
import WorkflowRunRow from '@/components/WorkflowRunRow.vue'
import { workflowRunsApi } from '@/api/workflowRuns'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import { notifyFailure, notifySuccess, notifyWarning, WORKFLOWS_SHELL_ROUTE } from '@/utils/notify'
import {
  filterAndSortRuns,
  RUN_STATUS_VALUES,
  type RunFilter,
  type RunSort,
} from '@/utils/runFilters'
import {
  ACTIVE_RUN_STATES,
  canClean,
  CLEANUP_IN_PROGRESS,
  statusColor,
  type RunAction,
} from '@/utils/status'
import type { WorkflowRun } from '@/types/schemas'

// workflow-api syncs run states from the engine every 30 s, so polling more
// often than this shows nothing new.
const POLL_INTERVAL_MS = 15_000
const LOAD_ERROR_TEXT = 'The workflow runs could not be loaded.'

const router = useRouter()
const failureDetails = useFailureDetailsStore()

const runs = ref<WorkflowRun[]>([])
const loading = ref(false)
const refreshing = ref(false)
const loadError = ref<ApiErrorInfo | null>(null)
const pollFailureReported = ref(false)

const appliedFilters = ref<RunFilter[]>([])
const searchText = ref('')
const sort = ref<RunSort>({ field: 'created_at', direction: 'desc' })

const tableHeaders = [
  { title: 'Status', key: 'lifecycle_status', sortable: false, width: '130px' },
  { title: 'Workflow', key: 'workflow', sortable: false },
  { title: 'Created', key: 'created_at', sortable: false, width: '150px' },
  { title: 'Updated', key: 'updated_at', sortable: false, width: '150px' },
  { title: 'External ID', key: 'external_id', sortable: false, width: '200px' },
  { title: 'Data', key: 'cleanup_status', sortable: false, width: '150px' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' as const, width: '240px' },
]

const visibleRuns = computed(() =>
  filterAndSortRuns(runs.value, appliedFilters.value, searchText.value, sort.value),
)

const statusStatistics = computed(() => {
  const stats: Record<string, number> = {}
  for (const run of runs.value) stats[run.lifecycle_status] = (stats[run.lifecycle_status] ?? 0) + 1
  return Object.fromEntries(RUN_STATUS_VALUES.filter((s) => stats[s]).map((s) => [s, stats[s]]))
})

function isStatusFilter(f: RunFilter, status: string) {
  return (
    f.field === 'status' && f.operator === '=' && f.value.toLowerCase() === status.toLowerCase()
  )
}

function isStatusFiltered(status: string) {
  return appliedFilters.value.some((f) => isStatusFilter(f, status))
}

function toggleStatusFilter(status: string) {
  appliedFilters.value = isStatusFiltered(status)
    ? appliedFilters.value.filter((f) => !isStatusFilter(f, status))
    : [...appliedFilters.value, { field: 'status', operator: '=', value: status }]
}

function clearFilters() {
  appliedFilters.value = []
  searchText.value = ''
}

// --- loading and polling ---

async function loadRuns(options: { silent?: boolean } = {}) {
  if (loading.value || refreshing.value) return
  const initial = runs.value.length === 0 && !options.silent
  if (initial) loading.value = true
  else if (!options.silent) refreshing.value = true
  const actionsBefore = finishedActions
  try {
    const loaded = await workflowRunsApi.getAll()
    if (actionsBefore === finishedActions) runs.value = loaded
    loadError.value = null
    pollFailureReported.value = false
  } catch (err) {
    if (runs.value.length === 0) {
      loadError.value = apiErrorInfo(err)
    } else if (!options.silent) {
      notifyFailure(
        'Could not refresh the workflow runs',
        'The list shows the last loaded state.',
        err,
      )
    } else if (!pollFailureReported.value) {
      pollFailureReported.value = true
      notifyFailure(
        'Automatic update failed',
        'The workflow runs could not be updated. The list shows the last loaded state.',
        err,
      )
    }
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function showLoadErrorDetails() {
  if (loadError.value) {
    failureDetails.show({
      title: 'Could not load the workflow runs',
      text: LOAD_ERROR_TEXT,
      error: loadError.value,
    })
  }
}

const hasActiveRuns = computed(() =>
  runs.value.some(
    (r) =>
      ACTIVE_RUN_STATES.includes(r.lifecycle_status) ||
      CLEANUP_IN_PROGRESS.includes(r.cleanup_status ?? 'not_required'),
  ),
)
const pageVisible = ref(document.visibilityState === 'visible')
const polling = computed(() => hasActiveRuns.value && !loadError.value)
let pollTimer: ReturnType<typeof setInterval> | null = null

function onVisibilityChange() {
  pageVisible.value = document.visibilityState === 'visible'
}

watch(
  () => polling.value && pageVisible.value && !confirmOpen.value,
  (active) => {
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = active ? setInterval(() => loadRuns({ silent: true }), POLL_INTERVAL_MS) : null
  },
)

onMounted(() => {
  document.addEventListener('visibilitychange', onVisibilityChange)
  loadRuns()
})

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisibilityChange)
  if (pollTimer) clearInterval(pollTimer)
})

// --- actions ---

const busyRuns = ref<Record<number, RunAction>>({})
let finishedActions = 0

function setBusy(ids: number[], action: RunAction | null) {
  const next = { ...busyRuns.value }
  for (const id of ids) {
    if (action) next[id] = action
    else delete next[id]
  }
  busyRuns.value = next
}

function replaceRun(updated: WorkflowRun) {
  runs.value = runs.value.map((r) => (r.id === updated.id ? updated : r))
}

function removeRun(run: WorkflowRun) {
  runs.value = runs.value.filter((r) => r.id !== run.id)
}

function runName(run: WorkflowRun) {
  return `${run.workflow?.title ?? 'Unknown workflow'} v${run.workflow?.increment ?? 0}`
}

async function runAction(
  run: WorkflowRun,
  action: RunAction,
  call: () => Promise<WorkflowRun | void>,
  success: string,
  failure: [string, string],
  onDone: (result: WorkflowRun | void) => void = (updated) => updated && replaceRun(updated),
) {
  setBusy([run.id], action)
  try {
    onDone(await call())
    finishedActions++
    notifySuccess(success, `${runName(run)} (run ${run.id})`)
  } catch (err) {
    notifyFailure(failure[0], failure[1], err)
  } finally {
    setBusy([run.id], null)
  }
}

function cancelRun(run: WorkflowRun) {
  return runAction(run, 'cancel', () => workflowRunsApi.cancel(run.id), 'Run canceled', [
    'Could not cancel the run',
    `Run ${run.id} of ${runName(run)} could not be canceled.`,
  ])
}

function retryRun(run: WorkflowRun) {
  return runAction(run, 'retry', () => workflowRunsApi.retry(run.id), 'Run retried', [
    'Could not retry the run',
    `Run ${run.id} of ${runName(run)} could not be retried.`,
  ])
}

function cleanRun(run: WorkflowRun) {
  return runAction(run, 'clean', () => workflowRunsApi.clean(run.id), 'Data cleanup queued', [
    'Could not clean the run data',
    `The data of run ${run.id} of ${runName(run)} could not be cleaned.`,
  ])
}

function deleteRun(run: WorkflowRun) {
  return runAction(
    run,
    'delete',
    () => workflowRunsApi.delete(run.id),
    'Run deleted',
    ['Could not delete the run', `Run ${run.id} of ${runName(run)} could not be deleted.`],
    () => removeRun(run),
  )
}

const eligibleForCleanup = computed(() => runs.value.filter(canClean))
const cleanupRunning = ref(false)

async function cleanAllFinished() {
  const targets = eligibleForCleanup.value.slice()
  const ids = targets.map((r) => r.id)
  cleanupRunning.value = true
  setBusy(ids, 'clean')
  try {
    const results = await Promise.allSettled(targets.map((r) => workflowRunsApi.clean(r.id)))
    results.forEach((r) => r.status === 'fulfilled' && replaceRun(r.value))
    finishedActions++
    const failed = results.filter((r) => r.status === 'rejected') as PromiseRejectedResult[]
    if (failed.length === 0) {
      notifySuccess(
        'Data cleanup queued',
        `${targets.length} finished ${targets.length === 1 ? 'run' : 'runs'}`,
      )
    } else if (failed.length === results.length) {
      notifyFailure('Could not clean the run data', 'No cleanup could be queued.', failed[0].reason)
    } else {
      notifyWarning(
        'Some cleanups failed',
        `Cleanup was queued for ${results.length - failed.length} runs. ${failed.length} could not be queued; try again for those.`,
      )
    }
  } finally {
    cleanupRunning.value = false
    setBusy(ids, null)
  }
}

type ConfirmTarget =
  { kind: 'cancel' | 'clean' | 'delete'; run: WorkflowRun } | { kind: 'bulk'; count: number }
const confirmTarget = ref<ConfirmTarget | null>(null)
const confirmOpen = ref(false)

function ask(target: ConfirmTarget) {
  confirmTarget.value = target
  confirmOpen.value = true
}

function askCancel(run: WorkflowRun) {
  ask({ kind: 'cancel', run })
}

function askCleanup(run: WorkflowRun) {
  ask({ kind: 'clean', run })
}

function askDelete(run: WorkflowRun) {
  ask({ kind: 'delete', run })
}

function askBulkCleanup() {
  ask({ kind: 'bulk', count: eligibleForCleanup.value.length })
}

const confirmContent = computed(() => {
  const target = confirmTarget.value
  if (target?.kind === 'cancel') {
    return {
      title: `Cancel run ${target.run.id}?`,
      text: `${runName(target.run)} stops. Running tasks are aborted and tasks that have not started yet do not run.`,
      confirmText: 'Cancel run',
      cancelText: 'Keep running',
    }
  }
  if (target?.kind === 'clean') {
    return {
      title: `Clean the data of run ${target.run.id}?`,
      text:
        `The data directory of ${runName(target.run)} is deleted from the workflow volume. ` +
        'Logs and run details are kept. This cannot be undone.',
      confirmText: 'Clean data',
      cancelText: 'Cancel',
    }
  }
  if (target?.kind === 'delete') {
    return {
      title: `Delete run ${target.run.id}?`,
      text:
        `${runName(target.run)} is removed with its data, task logs and run details. ` +
        'This cannot be undone.',
      confirmText: 'Delete run',
      cancelText: 'Cancel',
    }
  }
  const count = target?.kind === 'bulk' ? target.count : 0
  return {
    title: `Clean the data of ${count} finished ${count === 1 ? 'run' : 'runs'}?`,
    text:
      'The data directories of all completed, failed and canceled runs that still have data are deleted from ' +
      'the workflow volume. Logs and run details are kept. This cannot be undone.',
    confirmText: 'Clean data',
    cancelText: 'Cancel',
  }
})

function executeConfirmed() {
  const target = confirmTarget.value
  if (target?.kind === 'cancel') cancelRun(target.run)
  else if (target?.kind === 'clean') cleanRun(target.run)
  else if (target?.kind === 'delete') deleteRun(target.run)
  else if (target?.kind === 'bulk') cleanAllFinished()
}

function viewLogs(run: WorkflowRun) {
  router.push({ name: 'WorkflowRunLogs', params: { runId: run.id } })
}
</script>

<style scoped>
/* A readable maximum for a seven-column table; the container centres itself
   in the space beyond it. */
.runs-view {
  max-width: 1600px;
}
</style>
