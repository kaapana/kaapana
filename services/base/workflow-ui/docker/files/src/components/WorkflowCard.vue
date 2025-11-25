<template>
  <v-card class="d-flex flex-column h-100">
  <v-card-title class="d-flex align-center text-left workflow-title">
      <v-icon size="small" class="mr-2 text-primary flex-shrink-0">mdi-sitemap-outline</v-icon>
      <span class="text-truncate-multiline">{{ workflow.title }}</span>
    </v-card-title>

    <v-card-subtitle v-if="providers.length" class="pb-1 text-left">
      <strong>Provider:</strong> {{ providers.join(', ') }}
    </v-card-subtitle>
    <v-card-subtitle v-if="categories.length" class="pt-0 pb-2 text-left">
      <strong>Categories:</strong> {{ categories.join(', ') }}
    </v-card-subtitle>

    <!-- Description area with fixed height -->
  <v-card-text class="flex-grow-1 d-flex flex-column">
      <v-sheet :border="true" rounded class="pa-3 description-container">
        <div v-if="description" class="text-body-2">
          {{ description }}
        </div>
        <div v-else class="text-body-2 text-disabled font-italic">
          No description available
        </div>
      </v-sheet>
    </v-card-text>

    <!-- Footer: version selector and button -->
    <v-card-actions class="pt-0">
      <v-row dense>
        <v-col cols="6" v-if="versions && versions.length > 1">
          <v-select v-model="selectedVersion" :items="versions.map(v => ({ title: `v${v.version}`, value: v.version }))"
            label="Version" density="compact" variant="outlined" hide-details />
        </v-col>
        <v-col :cols="versions && versions.length > 1 ? 6 : 12">
          <v-btn color="primary" variant="elevated" block @click.stop="openForm">
            START
          </v-btn>
        </v-col>
      </v-row>
    </v-card-actions>

    <!-- Run Form -->
    <WorkflowRunForm v-model="showForm" :workflow="selectedWorkflow" :submitting="submitting" @submit="handleSubmit" />
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Workflow, Label, WorkflowRunCreate } from '@/types/schemas'
import { workflowRunsApi } from '@/api/workflowRuns'
import WorkflowRunForm from './WorkflowForm.vue'

const props = defineProps<{
  workflow: Workflow
  versions?: Workflow[]
}>()

const emit = defineEmits<{
  (e: 'workflowRunCreated', workflowRunId: number): void
}>()

const providers = computed(() =>
  props.workflow.labels
    .filter((l: Label) => l.key === 'kaapana-ui.provider')
    .map((l: Label) => l.value)
)

const categories = computed(() =>
  props.workflow.labels
    .filter((l: Label) => l.key === 'kaapana-ui.category')
    .map((l: Label) => l.value)
)

const description = computed(() => {
  const label = props.workflow.labels.find(
    (l: Label) => l.key === 'kaapana-ui.description'
  )
  return label ? label.value : null
})

const selectedVersion = ref<number | null>(
  props.versions?.[0]?.version ?? null
)

// Get the selected workflow based on version
const selectedWorkflow = computed(() => {
  if (!selectedVersion.value || !props.versions) return props.workflow
  return props.versions.find(v => v.version === selectedVersion.value) || props.workflow
})

// Form dialog state
const showForm = ref(false)
const submitting = ref(false)

// Open form dialog
const openForm = () => {
  showForm.value = true
}

// Handle form submission
const handleSubmit = async (workflowRunCreate: WorkflowRunCreate) => {
  submitting.value = true

  try {
    console.log('Submitting workflow run:', workflowRunCreate)

    const workflowRun = await workflowRunsApi.create(workflowRunCreate)

    console.log('Workflow run created successfully:', workflowRun)

    // Close the form on success
    showForm.value = false

    // Emit event to notify parent component
    emit('workflowRunCreated', workflowRun.id)

    // TODO: Show success notification
    // Example: useSnackbar().success(`Workflow "${workflowRun.workflow.title}" started successfully!`)

  } catch (error) {
    console.error('Failed to create workflow run:', error)

    // TODO: Show error notification
    // Example: useSnackbar().error(error instanceof Error ? error.message : 'Failed to start workflow')

    // Keep form open on error so user can retry
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.workflow-title {
  /* slightly smaller title area to avoid forcing tall cards */
  min-height: 48px;
  align-items: flex-start !important;
  padding-top: 8px;
}


.description-container {
  /* let the description area flex to fill remaining space inside the card
     instead of enforcing fixed min/max heights which can make the card larger
     than its container */
  flex: 1 1 auto;
  overflow: auto;
}
</style>