<template>
    <v-dialog v-model="isOpen" max-width="900px" scrollable>
        <v-card>
            <v-card-title class="d-flex align-start bg-primary py-4">
                <v-icon class="mr-3 mt-1" size="large">mdi-play-circle</v-icon>
                <div class="d-flex flex-column flex-grow-1 min-width-0">
                    <span class="text-caption text-medium-emphasis">Run Workflow</span>
                    <span class="text-h6 font-weight-bold workflow-title">{{ workflow.title }}</span>
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

                <div v-else-if="vueformSchema">
                    <div class="d-flex align-center mb-4 task-controls">
                        <v-btn small text @click="expandAll">Expand all</v-btn>
                        <v-btn small text @click="collapseAll">Collapse all</v-btn>
                        <v-spacer />
                    </div>

                    <div class="tasks-list mb-4" v-if="workflow.parameters && Object.keys(workflow.parameters).length">
                        <div v-for="(params, taskTitle) in workflow.parameters" class="task-block">
                            <div class="d-flex align-center task-header-row" @click="toggleTask(taskTitle)">
                                <div class="task-title">{{ taskTitle }}</div>
                                <v-spacer />
                                <div class="text-caption text-medium-emphasis">{{ params.length }} parameters</div>
                            </div>
                        </div>
                    </div>
                    <Vueform ref="form$" :schema="vueformSchema" :endpoint="false" @submit="handleSubmit"
                        :display-errors="false" class="workflow-vueform" />
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
import { ref, computed, watch, onBeforeUnmount, toRaw } from 'vue'
import type { Workflow, WorkflowParameter, WorkflowParameterUI } from '@/types/workflow'
import type { WorkflowRunCreate } from '@/types/workflowRun'

const props = defineProps<{
    workflow: Workflow
    modelValue: boolean
    submitting?: boolean
}>()

const emit = defineEmits<{
    (e: 'update:modelValue', value: boolean): void
    (e: 'submit', data: WorkflowRunCreate): void
}>()

const isOpen = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value)
})

const loading = ref(false)
const error = ref<string | null>(null)
const vueformSchema = ref<Record<string, any> | null>(null)
const form$ = ref<any>(null)

// Track which tasks are open/expanded
const taskOpen = ref<Record<string, boolean>>({})

// Grouped workflow parameters (task -> WorkflowParameter[])
const groupedParams = ref<Record<string, WorkflowParameter[]>>({})

// Helper to safely stringify possibly proxied or cyclic objects for debugging
function stringifySafe(obj: any): string {
    try {
        // try to unwrap Vue proxy first
        const raw = toRaw(obj as any)
        return JSON.stringify(raw, null, 2)
    } catch (err) {
        try {
            const seen = new WeakSet()
            return JSON.stringify(obj, function (_k, v) {
                if (v && typeof v === 'object') {
                    if (seen.has(v)) return '[Circular]'
                    seen.add(v)
                }
                return v
            }, 2)
        } catch (err2) {
            return String(obj)
        }
    }
}

const toggleTask = (name: string) => {
    taskOpen.value[name] = !taskOpen.value[name]
    vueformSchema.value = buildVueformSchema(groupedParams.value)
}

const expandAll = () => {
    Object.keys(taskOpen.value).forEach(k => (taskOpen.value[k] = true))
    vueformSchema.value = buildVueformSchema(groupedParams.value)
}

const collapseAll = () => {
    Object.keys(taskOpen.value).forEach(k => (taskOpen.value[k] = false))
    vueformSchema.value = buildVueformSchema(groupedParams.value)
}

// Get workflow description from labels
const workflowDescription = computed(() => {
    const label = props.workflow.labels?.find(
        (l: any) => l.key === 'kaapana-ui.description'
    )
    return label?.value || null
})

// Watch for dialog opening to load form
watch(isOpen, async (newValue) => {
    if (newValue) {
        await loadForm()
        // attach keyboard shortcuts when dialog opens
        window.addEventListener('keydown', keydownHandler)
    }
})

// Load workflow parameters and build form
const loadForm = async () => {
    loading.value = true
    error.value = null

    try {
        console.debug('loadForm: props.workflow =', stringifySafe(props.workflow))
        // prefer new `parameters` map on the workflow
        const rawWorkflow = toRaw(props.workflow as any)
        if (rawWorkflow.parameters && Object.keys(rawWorkflow.parameters).length > 0) {
            console.debug('loadForm: using props.workflow.parameters (new format) keys:', Object.keys(rawWorkflow.parameters))
            console.debug('loadForm: using props.workflow.parameters (new format) summary:', Object.keys(rawWorkflow.parameters).map(k => ({ task: k, count: rawWorkflow.parameters[k]?.length ?? 0 })))
            groupedParams.value = rawWorkflow.parameters
            // initialize taskOpen map
            Object.keys(groupedParams.value).forEach(k => {
                if (taskOpen.value[k] === undefined) taskOpen.value[k] = true
            })
            const schema = buildVueformSchema(groupedParams.value)
            console.debug('loadForm: built vueformSchema from new parameters:', schema)
            vueformSchema.value = schema
        } else {
            console.debug('loadForm: no workflow.paramters found;')
            groupedParams.value = {}
            vueformSchema.value = null
        }
    } catch (err) {
        console.error('Failed to load workflow parameters:', err)
        error.value = 'Failed to load workflow parameters'
    } finally {
        loading.value = false
    }
}

// Type guard to check if ui_params is WorkflowParameterUI
function isWorkflowParameterUI(uiParams: any): uiParams is WorkflowParameterUI {
    return uiParams && typeof uiParams.type === 'string'
}
// Build Vueform schema from workflow parameters.
// Accept either a flat array or an already-grouped map (task -> WorkflowParameter[]).
function buildVueformSchema(params: Record<string, WorkflowParameter[]>): Record<string, any> {
    const schema: Record<string, any> = {}
    console.debug('buildVueformSchema: params keys:', Object.keys(params || {}))
    if (!params || Object.keys(params).length === 0) {
        console.debug('buildVueformSchema: no params provided or empty map')
    }

    let taskIndex = 0
    for (const [taskName, paramsList] of Object.entries(params)) {
        console.debug(`buildVueformSchema: task ${taskName} has ${paramsList?.length ?? 0} parameters`)
        // Add divider before each task (except the first one)
        if (taskIndex > 0) {
            schema[`divider_${taskIndex}`] = { type: 'static', content: '<hr/>' }
        }

        // Initialize taskOpen state
        if (taskOpen.value[taskName] === undefined) taskOpen.value[taskName] = true

        // Add task title with toggle
        schema[`task_title_${taskIndex}`] = {
            type: 'static',
            content: `<div class="task-header"><button class="task-toggle">${taskOpen.value[taskName] ? '▾' : '▸'}</button><span class="task-title">${taskName}</span></div>`,
        }

        // If task is open, add its fields
        if (taskOpen.value[taskName]) {
            for (const param of paramsList) {
                // Skip if not WorkflowParameterUI (could be DataSelectionUI)
                if (!isWorkflowParameterUI(param.ui_params)) {
                    console.warn(`Skipping parameter ${param.env_variable_name} - not a standard UI parameter`)
                    continue
                }

                const uiParams = param.ui_params
                const fieldConfig: Record<string, any> = {
                    type: uiParams.type === 'multiselect' ? 'select' : mapParameterType(uiParams.type),
                    label: param.title,
                }

                if (param.description) {
                    fieldConfig.description = param.description
                    fieldConfig.descriptionPosition = 'before'
                }

                if (uiParams.default !== undefined) {
                    if (uiParams.type === 'multiselect') {
                        if (Array.isArray(uiParams.default)) fieldConfig.default = uiParams.default
                        else if (uiParams.default === '' || uiParams.default === null) fieldConfig.default = []
                        else fieldConfig.default = [uiParams.default]
                    } else {
                        fieldConfig.default = uiParams.default
                    }
                } else if (uiParams.type === 'multiselect') {
                    fieldConfig.default = []
                }

                const rules: string[] = []
                if (param.required && uiParams.type !== 'boolean') rules.push('required')
                if (rules.length > 0) fieldConfig.rules = rules.join('|')

                if (uiParams.type === 'select' && uiParams.options) fieldConfig.items = uiParams.options

                if (uiParams.type === 'multiselect' && uiParams.options) {
                    fieldConfig.items = uiParams.options
                    fieldConfig.multiple = true
                    fieldConfig.chips = true
                    fieldConfig.searchable = true
                    fieldConfig.clearable = true
                    fieldConfig.hideSelected = false
                    fieldConfig.object = false
                }

                if (uiParams.type === 'number' || uiParams.type === 'integer') {
                    if (uiParams.minimum !== undefined) fieldConfig.min = uiParams.minimum
                    if (uiParams.maximum !== undefined) fieldConfig.max = uiParams.maximum
                    if (uiParams.step !== undefined) fieldConfig.step = uiParams.step
                }

                if (uiParams.type === 'textarea') fieldConfig.rows = uiParams.rows || 3
                if (uiParams.placeholder) fieldConfig.placeholder = uiParams.placeholder

                schema[param.env_variable_name] = fieldConfig
            }
        }

        taskIndex += 1
    }

    return schema
}

// Map parameter types to Vueform types
function mapParameterType(type: WorkflowParameterUI['type']): string {
    const typeMap: Record<WorkflowParameterUI['type'], string> = {
        'string': 'text',
        'text': 'text',
        'number': 'number',
        'integer': 'number',
        'boolean': 'toggle',
        'select': 'select',
        'multiselect': 'multiselect',
        'textarea': 'textarea',
        'date': 'date',
        'datetime': 'datetime',
        'file': 'file',
    }

    return typeMap[type] || 'text'
}

// Submit the form
const submitForm = async () => {
    if (form$.value) {
        await form$.value.validate()
        if (form$.value.invalid) {
            return
        }
        form$.value.submit()
    } else {
        // No parameters, just submit
        handleSubmit({})
    }
}

// Handle form submission
const handleSubmit = async (formData: any) => {
    console.log('Form submitted with data:', formData)
    console.log('Workflow ID:', props.workflow.id)

    // Create WorkflowRunCreate object
    const workflowRunCreate: WorkflowRunCreate = {
        workflow: {
            title: props.workflow.title,
            version: props.workflow.version
        },
        labels: props.workflow.labels || [],
        config: formData
    }

    // Emit to parent - parent will handle the actual API call
    emit('submit', workflowRunCreate)

    // Don't close immediately - let parent close after successful submission
    // isOpen.value = false
}

// Close form
const closeForm = () => {
    isOpen.value = false
}

// Reset form state
const resetForm = () => {
    vueformSchema.value = null
    error.value = null
}

// Keyboard handler: Escape to close, Enter to submit (unless in textarea/contenteditable or modifier keys)
function keydownHandler(e: KeyboardEvent) {
    try {
        if (e.key === 'Escape') {
            // Close/cancel the form
            closeForm()
            return
        }

        if (e.key === 'Enter') {
            // Ignore modified Enter presses
            if (e.shiftKey || e.ctrlKey || e.altKey || e.metaKey) return

            const active = document.activeElement as HTMLElement | null
            if (active) {
                const tag = active.tagName
                const isTextarea = tag === 'TEXTAREA'
                const isContentEditable = active.isContentEditable
                const isInput = tag === 'INPUT' && (active as HTMLInputElement).type !== 'hidden'

                // Don't submit when user is typing into a textarea or editable element
                if (isTextarea || isContentEditable) return

                // For inputs, allow Enter to submit except when input type is multi-line (handled above)
                if (!isInput && !active.closest('.workflow-vueform')) {
                    // Not inside the form - ignore
                    return
                }
            }

            e.preventDefault()
            // Trigger form submit
            submitForm()
        }
    } catch (err) {
        // swallow errors from unexpected DOM states
        // console.debug('keydownHandler error', err)
    }
}
</script>

<style scoped>
.workflow-title {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
    word-break: break-word;
    line-height: 1.3;
}

.min-width-0 {
    min-width: 0;
}

.task-header {
    display: flex;
    align-items: center;
}

.task-header .task-toggle {
    border: none;
    background: transparent;
    font-size: 1rem;
    margin-right: 8px;
    cursor: pointer;
}

.task-title {
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: rgba(0, 0, 0, 0.7);
    /* make it darker for readability */
}

.task-chip {
    cursor: pointer;
}

.workflow-vueform .v-field__input,
.workflow-vueform input,
.workflow-vueform textarea,
.workflow-vueform .v-select {
    background-color: rgba(255, 255, 255, 0.92);
    /* slightly off-white */
}

.workflow-vueform .v-select .v-chip {
    background-color: rgba(0, 0, 0, 0.06);
}
</style>
