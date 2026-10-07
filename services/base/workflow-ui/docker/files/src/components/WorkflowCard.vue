<template>
  <v-card :elevation="2" class="d-flex flex-column workflow-card" data-testid="workflow-card">
    <v-card-item>
      <v-card-title class="text-wrap">{{ workflow.title }}</v-card-title>
      <v-card-subtitle v-if="providers.length" class="text-wrap">
        Provider: {{ providers.join(', ') }}
      </v-card-subtitle>
      <v-card-subtitle v-if="categories.length" class="text-wrap">
        Categories: {{ categories.join(', ') }}
      </v-card-subtitle>
    </v-card-item>

    <v-card-text class="flex-grow-1">
      <p v-if="description" class="text-body-2 workflow-description">{{ description }}</p>
      <p v-else class="text-body-2 text-medium-emphasis">No description available.</p>
    </v-card-text>

    <v-card-actions class="d-block px-4 pb-4">
      <div class="d-flex align-center ga-2">
        <v-select
          v-if="versions.length > 1"
          v-model="selectedIncrement"
          :items="versionItems"
          label="Version"
          density="compact"
          variant="outlined"
          hide-details
          class="version-select"
        />
        <v-btn
          color="primary"
          variant="flat"
          class="flex-grow-1"
          :prepend-icon="kaapanaIcons.start"
          :loading="tasksLoading"
          :disabled="tasksLoading || hasTasks !== true"
          @click="showForm = true"
        >
          Start
        </v-btn>
      </div>
      <p v-if="tasksError" class="text-caption text-error mt-2 mb-0">
        Could not check whether this workflow is ready.
        <a href="#" class="text-error" @click.prevent="loadTasks">Try again</a>
      </p>
      <p v-else-if="hasTasks === false" class="text-caption text-medium-emphasis mt-2 mb-0">
        Not ready yet: the workflow engine has not parsed this version. Refresh in a few minutes.
      </p>
    </v-card-actions>

    <WorkflowForm
      v-model="showForm"
      :workflow="workflow"
      :submitting="submitting"
      :submit-error="submitError"
      @submit="handleSubmit"
    />
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { apiErrorInfo, apiErrorText, kaapanaIcons } from '@kaapana/base-ui'
import WorkflowForm from './WorkflowForm.vue'
import { fetchWorkflowTasks } from '@/api/workflows'
import { workflowRunsApi } from '@/api/workflowRuns'
import type { FailureDetails } from '@/stores/failureDetails'
import {
  LABEL_CATEGORY,
  LABEL_DESCRIPTION,
  LABEL_PROVIDER,
  labelValue,
  labelValues,
} from '@/utils/labels'
import { notifySuccess, RUNS_SHELL_ROUTE } from '@/utils/notify'
import type { Workflow, WorkflowRunCreate } from '@/types/schemas'

const props = defineProps<{
  /** All revisions of one workflow, newest first. */
  versions: Workflow[]
}>()

const selectedIncrement = ref(props.versions[0]?.increment)

const workflow = computed(
  () => props.versions.find((v) => v.increment === selectedIncrement.value) ?? props.versions[0],
)
const versionItems = computed(() =>
  props.versions.map((v) => ({ title: `v${v.increment}`, value: v.increment })),
)

const providers = computed(() => labelValues(workflow.value, LABEL_PROVIDER))
const categories = computed(() => labelValues(workflow.value, LABEL_CATEGORY))
const description = computed(() => labelValue(workflow.value, LABEL_DESCRIPTION))

const tasksLoading = ref(false)
const tasksError = ref(false)
const hasTasks = ref<boolean | null>(null)

async function loadTasks() {
  const id = workflow.value.id
  tasksLoading.value = true
  tasksError.value = false
  try {
    const tasks = await fetchWorkflowTasks(id)
    if (id === workflow.value.id) hasTasks.value = tasks.length > 0
  } catch {
    if (id === workflow.value.id) {
      tasksError.value = true
      hasTasks.value = null
    }
  } finally {
    tasksLoading.value = false
  }
}

watch(() => workflow.value.id, loadTasks, { immediate: true })

const showForm = ref(false)
const submitting = ref(false)
const submitError = ref<FailureDetails | null>(null)

watch(showForm, (open) => {
  if (open) submitError.value = null
})

async function handleSubmit(payload: WorkflowRunCreate) {
  if (submitting.value) return
  submitting.value = true
  submitError.value = null
  try {
    await workflowRunsApi.create(payload)
    showForm.value = false
    notifySuccess(
      'Workflow run started',
      `${workflow.value.title} v${workflow.value.increment} was started. Select this message to open Workflow Runs.`,
      RUNS_SHELL_ROUTE,
    )
  } catch (err) {
    submitError.value = {
      title: 'Could not start the workflow',
      text: apiErrorText(err, 'The workflow run could not be created.'),
      error: apiErrorInfo(err),
    }
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.workflow-card {
  min-height: 280px;
}

.workflow-description {
  display: -webkit-box;
  -webkit-line-clamp: 6;
  line-clamp: 6;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.version-select {
  max-width: 110px;
}
</style>
