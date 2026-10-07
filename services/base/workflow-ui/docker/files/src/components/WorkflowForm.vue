<template>
  <v-dialog
    :model-value="modelValue"
    max-width="900"
    scrollable
    @update:model-value="onDialogUpdate"
  >
    <v-card :elevation="5">
      <v-card-item>
        <v-card-title class="text-wrap"
          >Start {{ workflow.title }} v{{ workflow.increment }}</v-card-title
        >
        <v-card-subtitle v-if="description" class="text-wrap">{{ description }}</v-card-subtitle>
      </v-card-item>

      <v-divider />

      <v-card-text>
        <v-form :id="formId" ref="formRef" @submit.prevent="submitForm">
          <h3 class="text-subtitle-1 font-weight-medium mb-2">General settings</h3>
          <v-expansion-panels v-model="generalPanel" multiple class="mb-6">
            <v-expansion-panel value="general" class="border border-opacity-25">
              <v-expansion-panel-title class="font-weight-medium">Run</v-expansion-panel-title>
              <v-expansion-panel-text eager>
                <v-select
                  v-model="cleanupPolicy"
                  :items="CLEANUP_POLICY_ITEMS"
                  label="Clean up run data"
                  hint="When the run's data directory on the workflow volume is deleted. Logs and run details are kept."
                  persistent-hint
                  variant="outlined"
                />
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <div class="d-flex align-center mb-2">
            <h3 class="text-subtitle-1 font-weight-medium">Task settings</h3>
            <v-spacer />
            <template v-if="taskNames.length">
              <v-btn variant="text" size="small" @click="expandedPanels = [...taskNames]"
                >Expand all</v-btn
              >
              <v-btn variant="text" size="small" @click="expandedPanels = []">Collapse all</v-btn>
            </template>
          </div>

          <v-expansion-panels
            v-if="taskNames.length"
            v-model="expandedPanels"
            multiple
            class="mb-4"
          >
            <v-expansion-panel
              v-for="taskName in taskNames"
              :key="taskName"
              :value="taskName"
              class="border border-opacity-25"
            >
              <v-expansion-panel-title>
                <span class="font-weight-medium">{{ taskName }}</span>
                <span class="text-medium-emphasis ms-2">
                  ({{ groupedParams[taskName].length }}
                  {{ groupedParams[taskName].length === 1 ? 'parameter' : 'parameters' }})
                </span>
              </v-expansion-panel-title>

              <v-expansion-panel-text eager>
                <div class="parameter-grid">
                  <template v-for="param in groupedParams[taskName]" :key="fieldKey(param)">
                    <v-switch
                      v-if="param.ui_form.type === 'bool'"
                      v-model="formData[fieldKey(param)]"
                      :label="param.ui_form.title"
                      :hint="param.ui_form.description"
                      persistent-hint
                      color="primary"
                    >
                      <template v-if="param.ui_form.help" #append>
                        <HelpIcon :text="param.ui_form.help" />
                      </template>
                    </v-switch>

                    <v-text-field
                      v-else-if="param.ui_form.type === 'int' || param.ui_form.type === 'float'"
                      v-model.number="formData[fieldKey(param)]"
                      :label="fieldLabel(param.ui_form)"
                      :hint="numberHint(param.ui_form)"
                      persistent-hint
                      type="number"
                      :step="param.ui_form.type === 'float' ? 'any' : 1"
                      variant="outlined"
                      :rules="numberRules(param.ui_form)"
                      validate-on="blur"
                    >
                      <template v-if="param.ui_form.help" #append-inner>
                        <HelpIcon :text="param.ui_form.help" />
                      </template>
                    </v-text-field>

                    <v-select
                      v-else-if="param.ui_form.type === 'list'"
                      v-model="formData[fieldKey(param)]"
                      :label="fieldLabel(param.ui_form)"
                      :hint="param.ui_form.description"
                      persistent-hint
                      :items="param.ui_form.options || []"
                      :multiple="!!param.ui_form.multiselectable"
                      :chips="!!param.ui_form.multiselectable"
                      :closable-chips="!!param.ui_form.multiselectable"
                      variant="outlined"
                      :rules="requiredRules(param.ui_form, 'Select')"
                      validate-on="blur"
                    >
                      <template v-if="param.ui_form.help" #append-inner>
                        <HelpIcon :text="param.ui_form.help" />
                      </template>
                    </v-select>

                    <v-autocomplete
                      v-else-if="param.ui_form.type === 'dataset'"
                      v-model="formData[fieldKey(param)]"
                      :label="fieldLabel(param.ui_form)"
                      :hint="param.ui_form.description"
                      persistent-hint
                      :items="datasets"
                      item-title="name"
                      item-value="name"
                      no-data-text="No datasets exist in this project yet."
                      variant="outlined"
                      prepend-inner-icon="mdi-database"
                      :loading="datasetsLoading"
                      :disabled="datasetsLoading"
                      :error-messages="
                        datasetsError ? 'The datasets could not be loaded.' : undefined
                      "
                      :rules="requiredRules(param.ui_form, 'Select')"
                      validate-on="blur"
                    >
                      <template v-if="param.ui_form.help" #append-inner>
                        <HelpIcon :text="param.ui_form.help" />
                      </template>
                      <template v-if="datasetsError" #append>
                        <v-btn
                          variant="text"
                          :prepend-icon="kaapanaIcons.refresh"
                          @click="loadDatasets"
                        >
                          Try again
                        </v-btn>
                      </template>
                    </v-autocomplete>

                    <v-checkbox
                      v-else-if="param.ui_form.type === 'terms'"
                      v-model="formData[fieldKey(param)]"
                      :label="param.ui_form.terms_text"
                      color="primary"
                      :rules="[
                        (v: boolean) => v === true || 'Accept the terms to start this workflow.',
                      ]"
                    />

                    <v-text-field
                      v-else
                      v-model="formData[fieldKey(param)]"
                      :label="fieldLabel(param.ui_form)"
                      :hint="param.ui_form.description"
                      persistent-hint
                      variant="outlined"
                      :prepend-inner-icon="
                        param.ui_form.type === 'data_entity' ? 'mdi-file-document' : undefined
                      "
                      :rules="stringRules(param.ui_form)"
                      validate-on="blur"
                    >
                      <template v-if="param.ui_form.help" #append-inner>
                        <HelpIcon :text="param.ui_form.help" />
                      </template>
                    </v-text-field>
                  </template>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <p v-else class="text-body-2 text-medium-emphasis mb-4">
            This workflow has no parameters to configure.
          </p>
        </v-form>

        <v-alert
          v-if="submitError"
          type="error"
          variant="tonal"
          class="mt-4"
          data-testid="submit-error"
        >
          {{ submitError.text }}
          <template #append>
            <v-btn variant="text" @click="failureDetails.show(submitError)">Details</v-btn>
          </template>
        </v-alert>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn :disabled="submitting" @click="requestClose">Cancel</v-btn>
        <v-btn
          color="primary"
          type="submit"
          :form="formId"
          :prepend-icon="kaapanaIcons.start"
          :loading="submitting"
          :disabled="submitting"
        >
          Start workflow
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <ConfirmDialog
    v-model="confirmDiscard"
    title="Discard changes?"
    :text="`The parameters you changed for ${workflow.title} will be lost.`"
    confirm-text="Discard changes"
    cancel-text="Keep editing"
    color="error"
    @confirm="close"
  />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, useId, watch } from 'vue'
import { ConfirmDialog, HelpIcon, kaapanaIcons, postViewDirty } from '@kaapana/base-ui'
import { fetchDatasets } from '@/api/datasets'
import { useFailureDetailsStore, type FailureDetails } from '@/stores/failureDetails'
import { LABEL_DESCRIPTION, labelValue } from '@/utils/labels'
import { CLEANUP_POLICY_ITEMS } from '@/utils/status'
import type {
  CleanupPolicy,
  Dataset,
  FloatUIForm,
  IntegerUIForm,
  StringUIForm,
  UIForm,
  Workflow,
  WorkflowParameter,
  WorkflowRunCreate,
} from '@/types/schemas'

const props = defineProps<{
  workflow: Workflow
  modelValue: boolean
  submitting?: boolean
  submitError?: FailureDetails | null
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'submit', data: WorkflowRunCreate): void
}>()

const failureDetails = useFailureDetailsStore()
const formId = `workflow-form-${useId()}`
const formRef = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)

const parameters = computed<WorkflowParameter[]>(() => props.workflow.workflow_parameters ?? [])
const description = computed(() => labelValue(props.workflow, LABEL_DESCRIPTION))

// Two tasks may use the same environment variable name, so the task title is
// part of the key.
function fieldKey(param: WorkflowParameter) {
  return `${param.task_title}::${param.env_variable_name}`
}

const groupedParams = computed(() => {
  const grouped: Record<string, WorkflowParameter[]> = {}
  for (const p of parameters.value) (grouped[p.task_title] ??= []).push(p)
  return grouped
})
const taskNames = computed(() => Object.keys(groupedParams.value))
const generalPanel = ref(['general'])
const expandedPanels = ref<string[]>([])

function defaultValue(param: WorkflowParameter): unknown {
  const form = param.ui_form
  if (form.default !== undefined && form.default !== null) return form.default
  switch (form.type) {
    case 'bool':
    case 'terms':
      return false
    case 'int':
    case 'float':
      return form.minimum ?? 0
    case 'list':
      return form.multiselectable ? [] : null
    default:
      return ''
  }
}

const formData = ref<Record<string, any>>({})
const cleanupPolicy = ref<CleanupPolicy>('on_success')
let initialState = ''

function snapshot() {
  return JSON.stringify([formData.value, cleanupPolicy.value])
}

function resetForm() {
  formData.value = Object.fromEntries(parameters.value.map((p) => [fieldKey(p), defaultValue(p)]))
  cleanupPolicy.value = 'on_success'
  generalPanel.value = ['general']
  expandedPanels.value = [...taskNames.value]
  initialState = snapshot()
}

watch(() => props.workflow, resetForm, { immediate: true })

const dirty = computed(() => snapshot() !== initialState)

watch(
  () => props.modelValue && dirty.value,
  (value) => postViewDirty(value),
)
onBeforeUnmount(() => {
  if (props.modelValue && dirty.value) postViewDirty(false)
})

const confirmDiscard = ref(false)

function onDialogUpdate(open: boolean) {
  if (!open) requestClose()
}

function requestClose() {
  if (props.submitting) return
  if (dirty.value) confirmDiscard.value = true
  else close()
}

function close() {
  emit('update:modelValue', false)
  resetForm()
}

// Datasets come from kaapana-backend; load them when a dataset field is shown.
const datasets = ref<Dataset[]>([])
const datasetsLoading = ref(false)
const datasetsError = ref(false)
const hasDatasetParameter = computed(() =>
  parameters.value.some((p) => p.ui_form.type === 'dataset'),
)

async function loadDatasets() {
  datasetsLoading.value = true
  datasetsError.value = false
  try {
    datasets.value = await fetchDatasets()
  } catch {
    datasetsError.value = true
  } finally {
    datasetsLoading.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open && hasDatasetParameter.value) loadDatasets()
  },
)

// Validation messages say what is required and how to fix the value.
function isEmpty(v: unknown) {
  return v === null || v === undefined || v === '' || (Array.isArray(v) && v.length === 0)
}

function fieldLabel(form: UIForm) {
  return form.required ? form.title : `${form.title} (optional)`
}

function requiredRules(form: UIForm, verb: 'Select' | 'Enter') {
  return form.required
    ? [(v: unknown) => !isEmpty(v) || `${verb} ${form.title.toLowerCase()}.`]
    : []
}

function rangeText(form: IntegerUIForm | FloatUIForm) {
  const { minimum: min, maximum: max } = form
  if (min !== undefined && max !== undefined) return `between ${min} and ${max}`
  if (min !== undefined) return `of at least ${min}`
  if (max !== undefined) return `of at most ${max}`
  return ''
}

function numberHint(form: IntegerUIForm | FloatUIForm) {
  const range = rangeText(form)
  const kind = form.type === 'int' ? 'A whole number' : 'A number'
  const rangeHint = range ? `${kind} ${range}.` : ''
  return [form.description, rangeHint].filter(Boolean).join(' ')
}

function numberRules(form: IntegerUIForm | FloatUIForm) {
  const kind = form.type === 'int' ? 'a whole number' : 'a number'
  const expected = `Enter ${kind}${rangeText(form) ? ` ${rangeText(form)}` : ''}.`
  return [
    (v: unknown) => {
      if (isEmpty(v)) return form.required ? expected : true
      const n = Number(v)
      if (Number.isNaN(n)) return expected
      if (form.type === 'int' && !Number.isInteger(n)) return expected
      if (form.minimum !== undefined && n < form.minimum) return expected
      if (form.maximum !== undefined && n > form.maximum) return expected
      return true
    },
  ]
}

function stringRules(form: UIForm) {
  const rules = requiredRules(form, 'Enter')
  const pattern = (form as StringUIForm).regex_pattern
  if (pattern) {
    rules.push((v: unknown) => {
      if (isEmpty(v)) return true
      try {
        return (
          new RegExp(pattern).test(String(v)) ||
          `Enter a value that matches the pattern ${pattern}.`
        )
      } catch {
        return true
      }
    })
  }
  return rules
}

async function submitForm() {
  if (props.submitting) return
  const result = await formRef.value?.validate()
  if (result && !result.valid) {
    generalPanel.value = ['general']
    expandedPanels.value = [...taskNames.value]
    return
  }

  emit('submit', {
    workflow: { id: props.workflow.id, increment: props.workflow.increment },
    labels: props.workflow.labels ?? [],
    cleanup_policy: cleanupPolicy.value,
    // The backend reads the chosen values from each parameter's default.
    workflow_parameters: parameters.value.map((param) => ({
      task_title: param.task_title,
      env_variable_name: param.env_variable_name,
      ui_form: { ...param.ui_form, default: formData.value[fieldKey(param)] },
    })) as WorkflowParameter[],
  })
}

// A started run leaves nothing unsaved.
watch(
  () => props.modelValue,
  (open, wasOpen) => {
    if (!open && wasOpen) resetForm()
  },
)
</script>

<style scoped>
.parameter-grid {
  display: grid;
  gap: 16px;
}
</style>
