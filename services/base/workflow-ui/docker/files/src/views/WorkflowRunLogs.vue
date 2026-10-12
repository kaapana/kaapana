<template>
  <v-container fluid class="text-left logs-view">
    <v-btn
      variant="text"
      prepend-icon="mdi-arrow-left"
      class="mb-2 ms-n2"
      :to="{ name: 'WorkflowRuns' }"
    >
      Workflow runs
    </v-btn>

    <div class="d-flex flex-wrap align-center ga-3 mb-4">
      <h1 class="text-h4">{{ heading }}</h1>
      <v-chip v-if="run" :color="statusColor(run.lifecycle_status)" variant="outlined">
        {{ run.lifecycle_status }}
      </v-chip>
      <span v-if="run" class="text-body-2 text-medium-emphasis">Run {{ run.id }}</span>
    </div>

    <v-skeleton-loader v-if="loading && !run" type="table" data-testid="logs-loading" />

    <v-empty-state
      v-else-if="loadError"
      :icon="kaapanaIcons.error"
      color="error"
      size="56"
      :title="`Could not load run ${runId}`"
      text="The workflow service could not be reached or reported an error. Try again, or contact your administrator if it persists."
    >
      <template #actions>
        <v-btn color="primary" variant="text" :prepend-icon="kaapanaIcons.refresh" @click="loadRun">
          Try again
        </v-btn>
        <v-btn variant="text" @click="showLoadErrorDetails">Details</v-btn>
        <v-btn variant="text" :to="{ name: 'WorkflowRuns' }">Back to workflow runs</v-btn>
      </template>
    </v-empty-state>

    <template v-else-if="run">
      <RunParameters :run="run" />
      <LogViewer :run="run" />
    </template>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { apiErrorInfo, kaapanaIcons, type ApiErrorInfo } from '@kaapana/base-ui'
import LogViewer from '@/components/LogViewer.vue'
import RunParameters from '@/components/RunParameters.vue'
import { workflowRunsApi } from '@/api/workflowRuns'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import { notifyFailure } from '@/utils/notify'
import { statusColor } from '@/utils/status'
import type { WorkflowRun } from '@/types/schemas'

const props = defineProps<{ runId: number }>()

const router = useRouter()
const failureDetails = useFailureDetailsStore()
const run = ref<WorkflowRun | null>(null)
const loading = ref(false)
const loadError = ref<ApiErrorInfo | null>(null)
const heading = computed(() =>
  run.value
    ? `Details of ${run.value.workflow?.title ?? 'Unknown workflow'} v${run.value.workflow?.increment}`
    : `Details of run ${props.runId}`,
)

async function loadRun() {
  loading.value = true
  try {
    run.value = await workflowRunsApi.getById(props.runId)
    loadError.value = null
  } catch (err) {
    run.value = null
    if (apiErrorInfo(err).status === 404) {
      notifyFailure(
        `Run ${props.runId} does not exist`,
        'It may have been deleted or belong to another project.',
        err,
      )
      router.replace({ name: 'WorkflowRuns' })
      return
    }
    loadError.value = apiErrorInfo(err)
  } finally {
    loading.value = false
  }
}

function showLoadErrorDetails() {
  if (loadError.value) {
    failureDetails.show({
      title: `Could not load run ${props.runId}`,
      text: 'The workflow run could not be loaded.',
      error: loadError.value,
    })
  }
}

onMounted(loadRun)
watch(() => props.runId, loadRun)
</script>

<style scoped>
.logs-view {
  max-width: 1800px;
}
</style>
