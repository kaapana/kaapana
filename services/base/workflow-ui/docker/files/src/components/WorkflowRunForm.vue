<template>
    <v-dialog v-model="isOpen" max-width="900px" scrollable>
        <v-card>
            <v-card-title class="d-flex align-start bg-primary py-4">
                <v-icon class="mr-3 mt-1" size="large">mdi-play-circle</v-icon>
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

                <div v-else-if="Object.keys(groupedParams).length" class="tasks-list mb-4">
                    <v-form>
                        <Vjsf v-model="jsonFormData" :schema="unifiedSchema" />
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
import { ref, computed } from 'vue'
import Vjsf from '@koumoul/vjsf'
import type { Workflow, WorkflowParameter, WorkflowParameterUI } from '@/types/workflow'
import type { WorkflowRunCreate } from '@/types/workflowRun'

const props = defineProps<{ workflow: Workflow; modelValue: boolean; submitting?: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'submit', data: WorkflowRunCreate): void }>()

const isOpen = computed({ get: () => props.modelValue, set: v => emit('update:modelValue', v) })
const loading = ref(false)
const error = ref<string | null>(null)

// https://koumoul-dev.github.io/vuetify-jsonschema-form/latest/editor
const jsonFormData = ref<Record<string, any>>({})

const groupedParams = computed<Record<string, WorkflowParameter[]>>(() => {
    const wf: any = props.workflow
    return wf.config_definition.workflow_parameters
})

const workflowDescription = computed(() => props.workflow?.labels?.find((l: any) => l.key === 'kaapana-ui.description')?.value || null)

// Build unified schema from groupedParams (fallback)
const unifiedSchema = computed(() => {
    const schema: any = { type: 'object', properties: {} }
    const tasks = Object.entries(groupedParams.value || {})
    if (!tasks.length) return schema

    for (const [taskName, params] of tasks) {
        const taskProps: any = {}
        const required: string[] = []
        for (const p of params) {
            if (!isWorkflowParameterUI(p.ui_params)) continue
            const ui = p.ui_params as WorkflowParameterUI
            const key = p.env_variable_name
            const base = mapJsonType(ui.type)
            const prop: any = { title: p.title || key, description: p.description || undefined, ...base }

            if ((ui.type === 'select' || ui.type === 'multiselect') && ui.options) {
                if (ui.type === 'multiselect') prop.items = { type: 'string', enum: ui.options }
                else prop.enum = ui.options
            }

            if (ui.default !== undefined && ui.default !== null) prop.default = ui.default
            if ((ui as any).minimum !== undefined) prop.minimum = Number((ui as any).minimum)
            if ((ui as any).maximum !== undefined) prop.maximum = Number((ui as any).maximum)
            if ((ui as any).step !== undefined) prop.step = Number((ui as any).step)

            if (p.required) required.push(key)
            taskProps[key] = prop
        }

        schema.properties[taskName] = { type: 'object', title: `${taskName} (${params.length})`, properties: taskProps, 'x-display': 'expansion-panels', 'x-props': { multiple: true } }
        if (required.length) schema.properties[taskName].required = required
    }

    return schema
})

function isWorkflowParameterUI(x: any): x is WorkflowParameterUI { return x && typeof (x as any).type === 'string' }

function mapJsonType(t: WorkflowParameterUI['type']) {
    return (t === 'number' || t === 'integer') ? { type: 'number' } : t === 'boolean' ? { type: 'boolean' } : t === 'multiselect' ? { type: 'array', items: { type: 'string' } } : { type: 'string' }
}

function submitForm() {
    const flat: Record<string, any> = {}
    // flatten jsonFormData into a single config object
    for (const [, taskData] of Object.entries(jsonFormData.value || {})) {
        if (taskData && typeof taskData === 'object') {
            for (const [key, value] of Object.entries(taskData)) {
                flat[key] = value
            }
        }
    }

    // Build a ConfigDefinition-like payload: list of WorkflowParameters with values
    const paramsList: WorkflowParameter[] = []

    for (const taskParams of Object.values(groupedParams.value || {})) {
        for (const p of taskParams) {
            const key = p.env_variable_name
            // choose value from form if present, otherwise fallback to ui default or parameter default
            const value = Object.prototype.hasOwnProperty.call(flat, key)
                ? flat[key]
                : (p.ui_params && (p.ui_params as any).default !== undefined ? (p.ui_params as any).default : (p as any).default)

            // don't mutate original parameter; create a shallow copy and attach the value
            const paramWithValue: any = { ...p, value }
            paramsList.push(paramWithValue)
        }
    }

    const payload: WorkflowRunCreate = {
        workflow: { title: props.workflow.title, version: props.workflow.version },
        labels: props.workflow.labels || [],
        // config is a ConfigDefinition-like object containing the list of workflow parameters
        config: { workflow_parameters: paramsList } as any,
    }

    emit('submit', payload)
    return
}

function closeForm() { isOpen.value = false }
</script>