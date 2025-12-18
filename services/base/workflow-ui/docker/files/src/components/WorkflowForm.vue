<template>
    <v-dialog v-model="isOpen" max-width="1000px" scrollable @keydown.enter="handleEnterKey">
        <v-card>
            <v-card-title class="d-flex bg-primary py-4">
                <v-icon class="mr-2 mt-1" size="x-large">mdi-sitemap-outline</v-icon>
                <div class="d-flex flex-column flex-grow-1 overflow-hidden">
                    <span class="text-caption text-medium-emphasis">Run Workflow</span>
                    <span class="text-h6 font-weight-bold text-truncate">{{ workflow.title }}</span>
                </div>
            </v-card-title>

            <v-divider />

            <v-card-text v-if="workflowDescription" class="py-3 bg-grey-darken-4">
                <div class="d-flex align-start">
                    <v-icon class="mr-2 mt-0" size="small" color="grey-lighten-1">mdi-information-outline</v-icon>
                    <div class="text-body-2 text-medium-emphasis">{{ workflowDescription }}</div>
                </div>
            </v-card-text>

            <v-divider v-if="workflowDescription" />

            <v-card-text class="pt-6 pb-4">
                <div v-if="loading" class="text-center py-8">
                    <v-progress-circular indeterminate color="primary" size="64" />
                    <p class="mt-4 text-body-1">Loading workflow parameters...</p>
                </div>

                <div v-else-if="error" class="text-center py-8">
                    <v-icon color="error" size="64">mdi-alert-circle</v-icon>
                    <p class="mt-4 text-body-1 text-error">{{ error }}</p>
                </div>

                <div v-else-if="Object.keys(groupedParams).length" class="mb-4">
                    <div class="d-flex justify-end mb-3 gap-2">
                        <v-btn size="small" variant="text" prepend-icon="mdi-chevron-down-box-outline"
                            @click="expandAll">
                            Expand All
                        </v-btn>
                        <v-btn size="small" variant="text" prepend-icon="mdi-chevron-up-box-outline"
                            @click="collapseAll">
                            Collapse All
                        </v-btn>
                    </div>
                    <v-form ref="formRef">
                        <v-expansion-panels v-model="expandedPanels" variant="accordion" multiple class="mb-2">
                            <v-expansion-panel v-for="(parameters, taskName) in groupedParams" :key="taskName"
                                elevation="2" class="mb-3 rounded-lg dark-panel">
                                <v-expansion-panel-title class="font-weight-medium panel-header">
                                    <div class="d-flex align-center">
                                        <v-icon class="mr-2" size="small" color="primary">mdi-cog</v-icon>
                                        <span>{{ taskName }}</span>
                                        <v-chip size="x-small" class="ml-2" color="primary" variant="tonal">
                                            {{ parameters.length }}
                                        </v-chip>
                                    </div>
                                </v-expansion-panel-title>

                                <v-expansion-panel-text class="panel-content">
                                    <div class="parameter-grid pa-4">
                                        <template v-for="param in parameters" :key="param.env_variable_name">
                                            <!-- Boolean Field -->
                                            <v-switch v-if="param.ui_form.type === 'bool'"
                                                v-model="formData[fieldKey(param)]" :label="param.ui_form.title"
                                                :hint="param.ui_form.description" persistent-hint color="primary"
                                                density="comfortable" class="parameter-field" :true-value="true"
                                                :false-value="false">
                                                <template v-if="param.ui_form.help" #append>
                                                    <v-tooltip location="top">
                                                        <template #activator="{ props: tooltipProps }">
                                                            <v-icon v-bind="tooltipProps" size="small" color="grey">
                                                                mdi-help-circle-outline
                                                            </v-icon>
                                                        </template>
                                                        {{ param.ui_form.help }}
                                                    </v-tooltip>
                                                </template>
                                            </v-switch>

                                            <!-- Integer Field -->
                                            <v-text-field v-else-if="param.ui_form.type === 'int'"
                                                v-model.number="formData[fieldKey(param)]"
                                                :label="param.ui_form.title + (param.ui_form.required ? ' *' : '')"
                                                :hint="getFieldHint(param.ui_form)" type="number" density="comfortable"
                                                variant="outlined" class="parameter-field no-spinners"
                                                :rules="getIntegerRules(param.ui_form)"
                                                :required="param.ui_form.required" validate-on="blur">
                                                <template v-if="param.ui_form.help" #append-inner>
                                                    <v-tooltip location="top">
                                                        <template #activator="{ props: tooltipProps }">
                                                            <v-icon v-bind="tooltipProps" size="small" color="grey">
                                                                mdi-help-circle-outline
                                                            </v-icon>
                                                        </template>
                                                        {{ param.ui_form.help }}
                                                    </v-tooltip>
                                                </template>
                                            </v-text-field>

                                            <!-- Float Field -->
                                            <v-text-field v-else-if="param.ui_form.type === 'float'"
                                                v-model.number="formData[fieldKey(param)]"
                                                :label="param.ui_form.title + (param.ui_form.required ? ' *' : '')"
                                                :hint="getFieldHint(param.ui_form)" type="number" step="any"
                                                density="comfortable" variant="outlined"
                                                class="parameter-field no-spinners"
                                                :rules="getFloatRules(param.ui_form)" :required="param.ui_form.required"
                                                validate-on="blur">
                                                <template v-if="param.ui_form.help" #append-inner>
                                                    <v-tooltip location="top">
                                                        <template #activator="{ props: tooltipProps }">
                                                            <v-icon v-bind="tooltipProps" size="small" color="grey">
                                                                mdi-help-circle-outline
                                                            </v-icon>
                                                        </template>
                                                        {{ param.ui_form.help }}
                                                    </v-tooltip>
                                                </template>
                                            </v-text-field>

                                            <!-- List Field (Multi-select) -->
                                            <v-select
                                                v-else-if="param.ui_form.type === 'list' && param.ui_form.multiselectable"
                                                v-model="formData[fieldKey(param)]"
                                                :label="param.ui_form.title + (param.ui_form.required ? ' *' : '')"
                                                :hint="param.ui_form.description" :items="param.ui_form.options || []"
                                                multiple chips closable-chips density="comfortable" variant="outlined"
                                                class="parameter-field" :rules="getRequiredRules(param.ui_form)"
                                                :required="param.ui_form.required" validate-on="blur">
                                                <template v-if="param.ui_form.help" #append-inner>
                                                    <v-tooltip location="top">
                                                        <template #activator="{ props: tooltipProps }">
                                                            <v-icon v-bind="tooltipProps" size="small" color="grey">
                                                                mdi-help-circle-outline
                                                            </v-icon>
                                                        </template>
                                                        {{ param.ui_form.help }}
                                                    </v-tooltip>
                                                </template>
                                            </v-select>

                                            <!-- List Field (Single-select) -->
                                            <v-select v-else-if="param.ui_form.type === 'list'"
                                                v-model="formData[fieldKey(param)]"
                                                :label="param.ui_form.title + (param.ui_form.required ? ' *' : '')"
                                                :hint="param.ui_form.description" :items="param.ui_form.options || []"
                                                density="comfortable" variant="outlined" class="parameter-field"
                                                :rules="getRequiredRules(param.ui_form)"
                                                :required="param.ui_form.required" validate-on="blur">
                                                <template v-if="param.ui_form.help" #append-inner>
                                                    <v-tooltip location="top">
                                                        <template #activator="{ props: tooltipProps }">
                                                            <v-icon v-bind="tooltipProps" size="small" color="grey">
                                                                mdi-help-circle-outline
                                                            </v-icon>
                                                        </template>
                                                        {{ param.ui_form.help }}
                                                    </v-tooltip>
                                                </template>
                                            </v-select>

                                            <!-- Dataset Field -->
                                            <v-select v-else-if="param.ui_form.type === 'dataset'"
                                                v-model="formData[fieldKey(param)]"
                                                :label="param.ui_form.title + (param.ui_form.required ? ' *' : '')"
                                                :hint="param.ui_form.description" :items="datasetOptions"
                                                item-title="name" item-value="name" density="comfortable"
                                                variant="outlined" class="parameter-field"
                                                :rules="getRequiredRules(param.ui_form)"
                                                :required="param.ui_form.required" validate-on="blur"
                                                :loading="datasetsLoading"
                                                :disabled="datasetsLoading || datasetsError !== null">
                                                <template #prepend-inner>
                                                    <v-icon size="small" color="grey">mdi-database</v-icon>
                                                </template>
                                                <template v-if="param.ui_form.help" #append-inner>
                                                    <v-tooltip location="top">
                                                        <template #activator="{ props: tooltipProps }">
                                                            <v-icon v-bind="tooltipProps" size="small" color="grey">
                                                                mdi-help-circle-outline
                                                            </v-icon>
                                                        </template>
                                                        {{ param.ui_form.help }}
                                                    </v-tooltip>
                                                </template>
                                                <template v-if="datasetsError" #message>
                                                    <span class="text-error">{{ datasetsError }}</span>
                                                </template>
                                            </v-select>

                                            <!-- Data Entity Field -->
                                            <v-text-field v-else-if="param.ui_form.type === 'data_entity'"
                                                v-model="formData[fieldKey(param)]"
                                                :label="param.ui_form.title + (param.ui_form.required ? ' *' : '')"
                                                :hint="param.ui_form.description" density="comfortable"
                                                variant="outlined" class="parameter-field"
                                                :rules="getRequiredRules(param.ui_form)"
                                                :required="param.ui_form.required" validate-on="blur">
                                                <template #prepend-inner>
                                                    <v-icon size="small" color="grey">mdi-file-document</v-icon>
                                                </template>
                                                <template v-if="param.ui_form.help" #append-inner>
                                                    <v-tooltip location="top">
                                                        <template #activator="{ props: tooltipProps }">
                                                            <v-icon v-bind="tooltipProps" size="small" color="grey">
                                                                mdi-help-circle-outline
                                                            </v-icon>
                                                        </template>
                                                        {{ param.ui_form.help }}
                                                    </v-tooltip>
                                                </template>
                                            </v-text-field>

                                            <!-- String Field (default) -->
                                            <v-text-field v-else-if="param.ui_form.type === 'str'"
                                                v-model="formData[fieldKey(param)]"
                                                :label="param.ui_form.title + (param.ui_form.required ? ' *' : '')"
                                                :hint="param.ui_form.description" density="comfortable"
                                                variant="outlined" class="parameter-field"
                                                :rules="getStringRules(param.ui_form)"
                                                :required="param.ui_form.required" validate-on="blur">
                                                <template v-if="param.ui_form.help" #append-inner>
                                                    <v-tooltip location="top">
                                                        <template #activator="{ props: tooltipProps }">
                                                            <v-icon v-bind="tooltipProps" size="small" color="grey">
                                                                mdi-help-circle-outline
                                                            </v-icon>
                                                        </template>
                                                        {{ param.ui_form.help }}
                                                    </v-tooltip>
                                                </template>
                                            </v-text-field>

                                            <!-- File Upload Field -->
                                            <v-file-input v-else-if="param.ui_form.type === 'file'"
                                                v-model="formData[fieldKey(param)]"
                                                :label="param.ui_form.title + (param.ui_form.required ? ' *' : '')"
                                                :hint="param.ui_form.description"
                                                :accept="param.ui_form.accept || undefined"
                                                :multiple="param.ui_form.multiple || false" density="comfortable"
                                                variant="outlined" class="parameter-field"
                                                :rules="getRequiredRules(param.ui_form)"
                                                :required="param.ui_form.required" validate-on="blur" prepend-icon=""
                                                prepend-inner-icon="mdi-paperclip" chips>
                                                <template #selection="{ fileNames }">
                                                    <v-chip v-for="fileName in fileNames" :key="fileName" size="small"
                                                        class="me-2">
                                                        {{ fileName }}
                                                    </v-chip>
                                                </template>
                                            </v-file-input>

                                            <!-- Terms and Conditions Field -->
                                            <v-checkbox v-else-if="param.ui_form.type === 'terms'"
                                                v-model="formData[fieldKey(param)]" color="primary"
                                                density="comfortable" class="parameter-field"
                                                :rules="[(v: boolean) => v === true || 'You must accept the terms to continue']">
                                                <template #label>
                                                    <span class="text-body-2">
                                                        {{ param.ui_form.terms_text }}
                                                        <v-icon size="small" color="primary"
                                                            class="ml-1">mdi-shield-check</v-icon>
                                                    </span>
                                                </template>
                                            </v-checkbox>
                                        </template>
                                    </div>
                                </v-expansion-panel-text>
                            </v-expansion-panel>
                        </v-expansion-panels>
                    </v-form>
                </div>

                <div v-else class="text-center py-8">
                    <v-icon size="64" color="info">mdi-check-circle</v-icon>
                    <p class="mt-4 text-body-1">This workflow has no configurable parameters.</p>
                    <p class="text-body-2 text-medium-emphasis">Click "Run Workflow" to start execution.</p>
                </div>
            </v-card-text>

            <v-divider />

            <v-card-actions class="pa-4">
                <v-spacer />
                <v-btn variant="text" size="large" @click="closeForm" :disabled="props.submitting">
                    Cancel
                </v-btn>
                <v-btn color="primary" variant="elevated" size="large" @click="submitForm" :disabled="loading"
                    :loading="props.submitting">
                    <v-icon class="mr-2">mdi-play</v-icon>
                    Run Workflow
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import type { Workflow, WorkflowRunCreate, WorkflowParameter, UIForm, IntegerUIForm, FloatUIForm, StringUIForm, Dataset } from '@/types/schemas'
import { fetchDatasets } from '@/api/datasetsApiClient'

const props = defineProps<{ workflow: Workflow; modelValue: boolean; submitting?: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'submit', data: WorkflowRunCreate): void }>()

const isOpen = computed({ get: () => props.modelValue, set: v => emit('update:modelValue', v) })
const loading = ref(false)
const error = ref<string | null>(null)
const formRef = ref<any>(null)
const formData = ref<Record<string, any>>({})

// Helper to create a unique key per task+env name so fields with the same
// env_variable_name but different tasks do not collide (e.g. two DATASET fields)
function fieldKey(param: WorkflowParameter) {
    return `${param.task_title}::${param.env_variable_name}`
}
const expandedPanels = ref<number[]>([])

// Dataset loading state
const datasetOptions = ref<Dataset[]>([])
const datasetsLoading = ref(false)
const datasetsError = ref<string | null>(null)

// Load datasets from kaapana-backend
async function loadDatasets() {
    datasetsLoading.value = true
    datasetsError.value = null
    try {
        datasetOptions.value = await fetchDatasets()
    } catch (err: any) {
        console.error('Failed to load datasets:', err)
        datasetsError.value = 'Failed to load datasets from kaapana-backend'
        datasetOptions.value = []
    } finally {
        datasetsLoading.value = false
    }
}

// Check if workflow has any dataset parameters
const hasDatasetParameters = computed(() => {
    const workflowParams: WorkflowParameter[] = (props.workflow as any).workflow_parameters || []
    return workflowParams.some(param => param.ui_form.type === 'dataset')
})

// Load datasets when dialog opens if there are dataset parameters
watch(isOpen, (newValue) => {
    if (newValue && hasDatasetParameters.value && datasetOptions.value.length === 0) {
        loadDatasets()
    }
})

// Expand/Collapse functions
function expandAll() {
    expandedPanels.value = Object.keys(groupedParams.value).map((_, index) => index)
}

function collapseAll() {
    expandedPanels.value = []
}

// Handle Enter key to submit form
function handleEnterKey(event: KeyboardEvent) {
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        event.preventDefault()
        submitForm()
    }
}

// Group workflow parameters by task_title -> { [task_title]: WorkflowParameter[] }
const groupedParams = computed<Record<string, WorkflowParameter[]>>(() => {
    const workflow: any = props.workflow
    const workflowParams: WorkflowParameter[] = workflow.workflow_parameters || []
    const grouped: Record<string, WorkflowParameter[]> = {}
    for (const p of workflowParams) {
        const key = p.task_title
        grouped[key] = grouped[key] || []
        grouped[key].push(p)
    }
    return grouped
})

const workflowDescription = computed(() =>
    props.workflow?.labels?.find((l: any) => l.key === 'kaapana-ui.description')?.value || null
)

// Initialize form data with default values
watch(
    () => props.workflow,
    (newWorkflow) => {
        if (newWorkflow) {
            const initialData: Record<string, any> = {}
            const workflowParams: WorkflowParameter[] = (newWorkflow as any).workflow_parameters || []

            for (const param of workflowParams) {
                const key = fieldKey(param)
                const defaultValue = param.ui_form.default

                // Set default value based on type
                if (defaultValue !== undefined && defaultValue !== null) {
                    initialData[key] = defaultValue
                } else {
                    switch (param.ui_form.type) {
                        case 'bool':
                            initialData[key] = false
                            break
                        case 'int':
                            initialData[key] = (param.ui_form as IntegerUIForm).minimum || 0
                            break
                        case 'float':
                            initialData[key] = (param.ui_form as FloatUIForm).minimum || 0.0
                            break
                        case 'list':
                            initialData[key] = param.ui_form.multiselectable ? [] : ''
                            break
                        case 'terms':
                            initialData[key] = false
                            break
                        default:
                            initialData[key] = ''
                    }
                }
            }

            formData.value = initialData

            // Expand all panels by default
            expandedPanels.value = Object.keys(groupedParams.value).map((_, index) => index)
        }
    },
    { immediate: true }
)

// Validation rule generators
function getRequiredRules(uiForm: UIForm) {
    const rules: Array<(v: any) => boolean | string> = []

    if (uiForm.required) {
        rules.push((v: any) => {
            if (Array.isArray(v)) {
                return v.length > 0 || `${uiForm.title} is required`
            }
            return (v !== null && v !== undefined && v !== '') || `${uiForm.title} is required`
        })
    }

    return rules
}

// Helper to generate hints with range information
function getFieldHint(uiForm: IntegerUIForm | FloatUIForm): string {
    const parts: string[] = []

    if (uiForm.description) {
        parts.push(uiForm.description)
    }

    const ranges: string[] = []
    if (uiForm.minimum !== undefined && uiForm.maximum !== undefined) {
        ranges.push(`Range: ${uiForm.minimum} - ${uiForm.maximum}`)
    } else if (uiForm.minimum !== undefined) {
        ranges.push(`Min: ${uiForm.minimum}`)
    } else if (uiForm.maximum !== undefined) {
        ranges.push(`Max: ${uiForm.maximum}`)
    }

    if (ranges.length > 0) {
        parts.push(ranges.join(', '))
    }

    return parts.join(' | ')
}

function getIntegerRules(uiForm: IntegerUIForm) {
    const rules = [...getRequiredRules(uiForm)]

    rules.push((v: any) => {
        if (v === '' || v === null || v === undefined) {
            return uiForm.required ? `${uiForm.title} is required` : true
        }
        return Number.isInteger(Number(v)) || 'Must be an integer'
    })

    if (uiForm.minimum !== undefined) {
        rules.push((v: any) => {
            if (v === '' || v === null || v === undefined) return true
            return Number(v) >= uiForm.minimum! || `Must be at least ${uiForm.minimum}`
        })
    }

    if (uiForm.maximum !== undefined) {
        rules.push((v: any) => {
            if (v === '' || v === null || v === undefined) return true
            return Number(v) <= uiForm.maximum! || `Must be at most ${uiForm.maximum}`
        })
    }

    return rules
}

function getFloatRules(uiForm: FloatUIForm) {
    const rules = [...getRequiredRules(uiForm)]

    rules.push((v: any) => {
        if (v === '' || v === null || v === undefined) {
            return uiForm.required ? `${uiForm.title} is required` : true
        }
        return !isNaN(Number(v)) || 'Must be a number'
    })

    if (uiForm.minimum !== undefined) {
        rules.push((v: any) => {
            if (v === '' || v === null || v === undefined) return true
            return Number(v) >= uiForm.minimum! || `Must be at least ${uiForm.minimum}`
        })
    }

    if (uiForm.maximum !== undefined) {
        rules.push((v: any) => {
            if (v === '' || v === null || v === undefined) return true
            return Number(v) <= uiForm.maximum! || `Must be at most ${uiForm.maximum}`
        })
    }

    return rules
}

function getStringRules(uiForm: StringUIForm | UIForm) {
    const rules = [...getRequiredRules(uiForm)]

    if ('regex_pattern' in uiForm && uiForm.regex_pattern) {
        rules.push((v: any) => {
            if (!v && !uiForm.required) return true
            try {
                const regex = new RegExp(uiForm.regex_pattern)
                return regex.test(v) || `Must match pattern: ${uiForm.regex_pattern}`
            } catch {
                return true
            }
        })
    }

    return rules
}

async function submitForm() {
    // Temporarily expand all panels to ensure all fields are validated
    const previousExpandedState = [...expandedPanels.value]
    expandAll()

    // Wait for next tick to ensure fields are rendered
    await new Promise(resolve => setTimeout(resolve, 0))

    // Validate form
    if (formRef.value) {
        const { valid } = await formRef.value.validate()
        if (!valid) {
            // Keep panels expanded so user can see errors
            return
        }
    }

    // Restore previous expanded state
    expandedPanels.value = previousExpandedState

    const payload: WorkflowRunCreate = {
        workflow: { title: props.workflow.title, version: props.workflow.version },
        labels: props.workflow.labels || [],
        workflow_parameters: [],
    }

    // Build parameters array from form data with updated default values
    const workflowParams: WorkflowParameter[] = (props.workflow as any).workflow_parameters || []

    for (const param of workflowParams) {
        const envName = param.env_variable_name
        const value = formData.value[fieldKey(param)]

        // Create parameter with updated default value
        payload.workflow_parameters!.push({
            task_title: param.task_title,
            env_variable_name: envName,
            ui_form: {
                ...param.ui_form,
                default: value  // Update the default with the user-selected value
            }
        } as any)
    }

    emit('submit', payload)
}

function closeForm() {
    isOpen.value = false
    // Reset form on close
    if (formRef.value) {
        formRef.value.reset()
    }
    // Re-initialize form data with default values
    const workflowParams: WorkflowParameter[] = (props.workflow as any).workflow_parameters || []
    const initialData: Record<string, any> = {}

    for (const param of workflowParams) {
        const key = fieldKey(param)
        const defaultValue = param.ui_form.default

        if (defaultValue !== undefined && defaultValue !== null) {
            initialData[key] = defaultValue
        } else {
            switch (param.ui_form.type) {
                case 'bool':
                    initialData[key] = false
                    break
                case 'int':
                    initialData[key] = (param.ui_form as IntegerUIForm).minimum || 0
                    break
                case 'float':
                    initialData[key] = (param.ui_form as FloatUIForm).minimum || 0.0
                    break
                case 'list':
                    initialData[key] = param.ui_form.multiselectable ? [] : ''
                    break
                case 'terms':
                    initialData[key] = false
                    break
                default:
                    initialData[key] = ''
            }
        }
    }

    formData.value = initialData
}
</script>

<style scoped>
.parameter-grid {
    display: grid;
    gap: 20px;
    padding: 16px 0;
}

.parameter-field {
    width: 100%;
}

/* Expansion panel styling - dark background */
:deep(.panel-header) {
    background-color: rgb(var(--v-theme-surface-variant)) !important;
    color: rgb(var(--v-theme-on-surface)) !important;
}

:deep(.panel-header:hover) {
    background-color: rgba(var(--v-theme-surface-variant), 0.8) !important;
}

:deep(.panel-header.v-expansion-panel-title--active) {
    background-color: rgba(var(--v-theme-surface-bright), 0.95) !important;
}

:deep(.panel-header span) {
    color: rgb(var(--v-theme-on-surface)) !important;
}

:deep(.panel-content) {
    background-color: rgb(var(--v-theme-surface)) !important;
}

:deep(.dark-panel) {
    background-color: rgb(var(--v-theme-surface-variant)) !important;
}

/* Expansion panel title styling */
:deep(.v-expansion-panel-title) {
    padding: 16px 20px;
}

:deep(.v-expansion-panel-text__wrapper) {
    padding: 0 !important;
}

/* Form field enhancements */
:deep(.v-input__details) {
    padding-top: 4px;
    min-height: 20px;
}

/* Keep hints always visible for switches/checkboxes */
:deep(.v-switch .v-input__details),
:deep(.v-checkbox .v-input__details) {
    display: block !important;
}

/* Field error animation */
:deep(.v-field--error) {
    animation: shake 0.3s;
}

@keyframes shake {

    0%,
    100% {
        transform: translateX(0);
    }

    25% {
        transform: translateX(-5px);
    }

    75% {
        transform: translateX(5px);
    }
}

/* Hint text styling - keep white/light by default */
:deep(.v-input:not(.v-input--error) .v-messages__message) {
    color: rgba(var(--v-theme-on-surface), 0.7);
}

/* Error message styling - red when validation fails */
:deep(.v-input--error .v-messages__message) {
    color: rgb(var(--v-theme-error)) !important;
}

/* Hide number input spinners */
:deep(.no-spinners input[type="number"]::-webkit-outer-spin-button),
:deep(.no-spinners input[type="number"]::-webkit-inner-spin-button) {
    -webkit-appearance: none;
    appearance: none;
    margin: 0;
}

:deep(.no-spinners input[type="number"]) {
    -moz-appearance: textfield;
    appearance: textfield;
}
</style>
