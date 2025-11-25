<template>
    <div class="search-bar-root">
        <div class="panel-wrap pa-1" @click="handleContainerClick">
            <div class="filter-container px-3">
                <div class="filter-tokens-row">
                    <div v-for="(filter, index) in appliedFilters" :key="index" class="filter-token-group">
                        <span class="token" @click.stop="editFilterField(index)">{{ getFieldLabel(filter.field) }}</span>
                        <span class="token token-operator">=</span>
                        <span class="token token-value" @click.stop="editFilterValue(index)">
                            {{ getValueLabel(filter.field, filter.value) }}
                            <v-btn icon size="x-small" variant="text" @click.stop="removeFilter(index)"
                                class="token-close" title="Remove filter">
                                <v-icon size="12">mdi-close</v-icon>
                            </v-btn>
                        </span>
                    </div>

                    <div v-if="showFilterBuilder" class="filter-builder">
                        <div v-if="!buildingFilter.field" class="field-selector">
                            <v-menu v-model="_openFieldMenu" :close-on-content-click="false" location="bottom start">
                                <template #activator="{ props: menuProps }">
                                    <input ref="fieldInput" v-bind="menuProps" v-model="textSearchQuery"
                                        :placeholder="appliedFilters.length === 0 ? 'Type to query or search...' : ''"
                                        class="filter-input" @focus="showFilterBuilder = true" />
                                </template>
                                <v-card min-width="240">
                                    <v-list density="compact">
                                        <v-list-item v-for="field in filteredFields" :key="field.key"
                                            @click="selectField(field)">
                                            <template #prepend>
                                                <v-icon :icon="field.icon" size="16" />
                                            </template>
                                            <v-list-item-title>{{ field.label }}</v-list-item-title>
                                        </v-list-item>
                                        <v-list-item v-if="filteredFields.length === 0">
                                            <v-list-item-title class="text-caption text-medium-emphasis">No matching fields</v-list-item-title>
                                        </v-list-item>
                                    </v-list>
                                </v-card>
                            </v-menu>
                        </div>

                        <div v-else class="value-selector">
                            <span class="token">{{ getFieldLabel(buildingFilter.field) }}</span>
                            <span class="token token-operator">=</span>
                            <v-menu v-model="_openValueMenu" :close-on-content-click="false" location="bottom start">
                                <template #activator="{ props: menuProps }">
                                    <input ref="valueInput" v-bind="menuProps" v-model="valueSearchQuery"
                                        :placeholder="`Type or select ${getFieldLabel(buildingFilter.field)}...`"
                                        class="filter-input" @keydown.escape="resetBuilder"
                                        @keydown.enter="handleValueEnter" autofocus />
                                </template>
                                <v-card min-width="240" max-height="320">
                                    <v-list density="compact">
                                        <div v-if="getValuesForField(buildingFilter.field).length > 0">
                                            <v-list-item v-for="val in filteredValues" :key="val.value"
                                                @click="selectValue(val)">
                                                <v-list-item-title>
                                                    <v-chip v-if="buildingFilter.field === 'status'"
                                                        :color="statusColor(val.label)" size="small" variant="outlined">
                                                        {{ val.label }}
                                                    </v-chip>
                                                    <span v-else>{{ val.label }}</span>
                                                </v-list-item-title>
                                            </v-list-item>
                                            <v-list-item v-if="filteredValues.length === 0">
                                                <v-list-item-title class="text-caption text-medium-emphasis">No
                                                    matches</v-list-item-title>
                                            </v-list-item>
                                        </div>

                                        <div v-else>
                                            <v-list-item>
                                                <v-list-item-title class="text-caption text-medium-emphasis">Type and
                                                    press
                                                    Enter</v-list-item-title>
                                            </v-list-item>
                                        </div>
                                    </v-list>
                                </v-card>
                            </v-menu>
                        </div>
                    </div>

                    <div v-if="appliedFilters.length === 0 && !showFilterBuilder" class="initial-input">
                        <input ref="initialInput" v-model="textSearchQuery" placeholder="Type to query or search..."
                            class="filter-input" @focus="showFilterBuilder = true" />
                    </div>
                </div>

                <div class="filter-actions">
                    <v-btn v-if="appliedFilters.length > 0 || textSearchQuery" icon size="small" variant="text"
                        @click.stop="clearAllFilters" title="Clear all filters" class="action-btn">
                        <v-icon class="">mdi-close</v-icon>
                    </v-btn>

                    <v-btn size="small" variant="outlined" class="action-btn search-btn" @click.stop="applySearch" title="Apply search">
                        <v-icon>mdi-magnify</v-icon>
                    </v-btn>

                    <v-menu location="bottom end">
                        <template #activator="{ props: menuProps }">
                            <v-btn v-bind="menuProps" size="small" variant="text" @click.stop title="Sort by" class="action-btn">
                                <v-icon>mdi-sort</v-icon>
                            </v-btn>
                        </template>
                        <v-list density="compact">
                            <v-list-subheader>Sort by</v-list-subheader>
                            <v-list-item @click="setSortField('created_at')">
                                <template #prepend>
                                    <v-icon v-if="sortField === 'created_at'">mdi-check</v-icon>
                                </template>
                                <v-list-item-title>Created Date</v-list-item-title>
                            </v-list-item>
                            <v-list-item @click="setSortField('status')">
                                <template #prepend>
                                    <v-icon v-if="sortField === 'status'">mdi-check</v-icon>
                                </template>
                                <v-list-item-title>Status</v-list-item-title>
                            </v-list-item>
                            <v-list-item @click="setSortField('workflow')">
                                <template #prepend>
                                    <v-icon v-if="sortField === 'workflow'">mdi-check</v-icon>
                                </template>
                                <v-list-item-title>Workflow</v-list-item-title>
                            </v-list-item>
                            <v-divider />
                            <v-list-item @click="toggleSortDirection">
                                <template #prepend>
                                    <v-icon>{{ sortDirection === 'desc' ? 'mdi-arrow-down' : 'mdi-arrow-up' }}</v-icon>
                                </template>
                                <v-list-item-title>{{ sortDirection === 'desc' ? 'Descending' : 'Ascending' }}</v-list-item-title>
                            </v-list-item>
                        </v-list>
                    </v-menu>

                    <v-btn icon size="small" variant="text" @click.stop="showHelp = true" title="Help" class="action-btn">
                        <v-icon>mdi-help-circle-outline</v-icon>
                    </v-btn>
                </div>
            </div>
        </div>

        <v-dialog v-model="showHelp" max-width="700">
            <v-card>
                <v-card-title class="d-flex align-center"><v-icon class="mr-2">mdi-help-circle</v-icon>Query Builder
                    Help</v-card-title>
                <v-card-text>
                    <p class="text-body-2 mb-3">Build queries by clicking in the query builder, selecting a field, and
                        choosing a
                        value.</p>
                    <div class="mb-4">
                        <h3 class="text-subtitle-2 mb-2">How to use:</h3>
                        <ol class="text-body-2 ml-4">
                            <li class="mb-1">Click in the search bar</li>
                            <li class="mb-1">Select a field</li>
                            <li class="mb-1">Choose or type a value</li>
                            <li class="mb-1">Click the magnifying glass or press Enter to apply</li>
                        </ol>
                    </div>
                </v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn color="primary" @click="showHelp = false">Got it</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, PropType, nextTick, onMounted } from 'vue'
import { statusColor } from '@/utils/status'
import type { WorkflowRun } from '@/types/schemas'

// Props
const props = defineProps({
    runs: { type: Array as PropType<WorkflowRun[]>, default: () => [] }
})
const emit = defineEmits(['update:filters', 'apply:filtered'])

// Local state
const showFilterBuilder = ref(false)
const showHelp = ref(false)
const textSearchQuery = ref('')
const valueSearchQuery = ref('')

const buildingFilter = ref<{ field: string | null; value: string | null }>({ field: null, value: null })
const appliedFilters = ref<{ field: string; value: string }[]>([])

// When editing an existing token, editingIndex points to that filter index. null means creating a new one.
const editingIndex = ref<number | null>(null)

// Sorting state
const sortField = ref<string>('created_at')
const sortDirection = ref<'asc' | 'desc'>('desc')

// Menu model toggles for v-menu
// start closed
const _openFieldMenu = ref(false)
const _openValueMenu = ref(false)

// Input refs
const fieldInput = ref<HTMLInputElement | null>(null)
const valueInput = ref<HTMLInputElement | null>(null)
const initialInput = ref<HTMLInputElement | null>(null)

// Emit initial filtered results on mount
onMounted(() => {
    emit('apply:filtered', filteredResults.value)
})

// Watch for changes in runs prop to re-emit filtered results
watch(() => props.runs, () => {
    emit('apply:filtered', filteredResults.value)
}, { deep: true })

// Field definitions
const availableFields = [
    { key: 'status', label: 'Status', icon: 'mdi-clock-outline', type: 'enum' },
    { key: 'workflow', label: 'Workflow', icon: 'mdi-sitemap-outline', type: 'string' },
    { key: 'external_id', label: 'External ID', icon: 'mdi-identifier', type: 'string' }
]

function getValuesForField(field: string | null) {
    if (field === 'status') {
        return [
            { value: 'created', label: 'Created' },
            { value: 'pending', label: 'Pending' },
            { value: 'scheduled', label: 'Scheduled' },
            { value: 'running', label: 'Running' },
            { value: 'completed', label: 'Completed' },
            { value: 'error', label: 'Error' },
            { value: 'canceled', label: 'Canceled' }
        ]
    } else if (field === 'workflow') {
        const uniqueTitles = [...new Set(props.runs.map(r => r.workflow?.title).filter(Boolean))]
        return uniqueTitles.map(t => ({ value: t as string, label: t as string }))
    }
    return []
}

const filteredValues = computed(() => {
    const values = getValuesForField(buildingFilter.value.field)
    if (!valueSearchQuery.value) return values
    const q = valueSearchQuery.value.toLowerCase()
    return values.filter(v => v.label.toLowerCase().includes(q))
})

const filteredFields = computed(() => {
    if (!textSearchQuery.value) return availableFields
    const q = textSearchQuery.value.toLowerCase()
    return availableFields.filter(f => f.label.toLowerCase().includes(q) || f.key.toLowerCase().includes(q))
})

function selectField(field: { key: string; label: string; icon: string; type: string }) {
    buildingFilter.value.field = field.key
    valueSearchQuery.value = ''
    textSearchQuery.value = ''
}

function selectValue(val: { value: string; label: string }) {
    if (!buildingFilter.value.field) return

    if (editingIndex.value !== null && editingIndex.value >= 0 && editingIndex.value < appliedFilters.value.length) {
        // replace existing filter
        appliedFilters.value.splice(editingIndex.value, 1, { field: buildingFilter.value.field, value: val.value })
    } else {
        appliedFilters.value.push({ field: buildingFilter.value.field, value: val.value })
    }

    // done editing/adding
    resetBuilder()
    editingIndex.value = null
    // Keep filter builder open to allow chaining
    showFilterBuilder.value = true
    }

// Edit a filter's field: open the field selector and prepare to replace the existing filter
function editFilterField(index: number) {
    const f = appliedFilters.value[index]
    // mark we're editing this filter
    editingIndex.value = index
    // open field selector and prefill the search so user can quickly pick another field
    textSearchQuery.value = getFieldLabel(f.field)
    buildingFilter.value = { field: null, value: f.value }
    showFilterBuilder.value = true
    // open the menu and focus the field input
    _openFieldMenu.value = true
    nextTick(() => fieldInput.value?.focus())
}

// Edit a filter's value: open the value selector for that field prefilled with the current value
function editFilterValue(index: number) {
    const f = appliedFilters.value[index]
    editingIndex.value = index
    buildingFilter.value = { field: f.field, value: f.value }
    // prefill the value input with the current token so they can edit it
    valueSearchQuery.value = f.value
    showFilterBuilder.value = true
    _openValueMenu.value = true
    nextTick(() => valueInput.value?.focus())
}

function handleValueEnter() {
    if (!buildingFilter.value.field || !valueSearchQuery.value) return

    if (editingIndex.value !== null && editingIndex.value >= 0 && editingIndex.value < appliedFilters.value.length) {
        appliedFilters.value.splice(editingIndex.value, 1, { field: buildingFilter.value.field, value: valueSearchQuery.value })
    } else {
        appliedFilters.value.push({ field: buildingFilter.value.field, value: valueSearchQuery.value })
    }

    resetBuilder()
    editingIndex.value = null
    // Keep filter builder open to allow chaining
    showFilterBuilder.value = true
}

function resetBuilder() {
    buildingFilter.value = { field: null, value: null }
    valueSearchQuery.value = ''
}

function removeFilter(index: number) {
    appliedFilters.value.splice(index, 1)
}

function clearAllFilters() {
    appliedFilters.value = []
    textSearchQuery.value = ''
    resetBuilder()
    showFilterBuilder.value = false
}

function getFieldLabel(key: string) {
    const f = availableFields.find(x => x.key === key)
    return f?.label || key
}

function getValueLabel(field: string, value: string) {
    const vals = getValuesForField(field)
    const v = vals.find(x => x.value === value)
    return v?.label || value
}

// statusColor imported from utils/status

// Emit filters to parent whenever they change
watch([appliedFilters, textSearchQuery], () => {
    emit('update:filters', { appliedFilters: appliedFilters.value.slice(), text: textSearchQuery.value })
    // Also emit the filtered results for convenience
    emit('apply:filtered', filteredResults.value)
}, { deep: true })

// Compute filtered results locally (useful for previewing or emitting)
const filteredResults = computed(() => {
    let result = [...props.runs]

    appliedFilters.value.forEach(filter => {
        if (filter.field === 'status') {
            result = result.filter(r => (r.lifecycle_status || '').toLowerCase() === filter.value.toLowerCase())
        } else if (filter.field === 'workflow') {
            const t = filter.value.toLowerCase()
            result = result.filter(r => (r.workflow?.title || '').toLowerCase().includes(t))
        } else if (filter.field === 'external_id') {
            const id = filter.value.toLowerCase()
            result = result.filter(r => (r.external_id || '').toLowerCase().includes(id))
        } else if (filter.field === 'created_at') {
            const fd = filter.value.toLowerCase()
            result = result.filter(r => new Date(r.created_at).toISOString().split('T')[0].includes(fd))
        }
    })

    if (textSearchQuery.value && appliedFilters.value.length === 0) {
        const q = textSearchQuery.value.toLowerCase()
        result = result.filter(r => {
            const text = [r.workflow?.title || '', r.external_id || '', r.lifecycle_status, String(r.id)].join(' ').toLowerCase()
            return text.includes(q)
        })
    }

    // Apply sorting
    result.sort((a, b) => {
        let comparison = 0
        
        if (sortField.value === 'created_at') {
            comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        } else if (sortField.value === 'status') {
            comparison = (a.lifecycle_status || '').localeCompare(b.lifecycle_status || '')
        } else if (sortField.value === 'workflow') {
            comparison = (a.workflow?.title || '').localeCompare(b.workflow?.title || '')
        }
        
        return sortDirection.value === 'desc' ? -comparison : comparison
    })

    return result
})

// Quick status statistics
const statusStatistics = computed(() => {
    const stats: Record<string, number> = {}
    for (const r of props.runs) {
        const s = r.lifecycle_status || 'Unknown'
        stats[s] = (stats[s] || 0) + 1
    }
    return stats
})

function applySearch() {
    // emit current filtered set explicitly
    emit('apply:filtered', filteredResults.value)
}

// Handle clicking anywhere in the container to focus input
function handleContainerClick(event: MouseEvent) {
    // Don't trigger when clicking on action buttons or native buttons/inputs
    const target = event.target as HTMLElement
    if (target.closest('.action-btn') || target.closest('.token-close') || target.closest('.v-btn')) {
        return
    }

    // Always open the builder and ensure the relevant menu/input is opened and focused
    showFilterBuilder.value = true
    nextTick(() => {
        if (buildingFilter.value.field) {
            // editing a value - open value menu and focus
            _openValueMenu.value = true
            // ensure value menu is toggled open so the activator input is visible
            valueInput.value?.focus()
        } else {
            // open field selector and focus regardless of prior state
            _openFieldMenu.value = true
            fieldInput.value?.focus()
        }
    })
}

// Sorting functions
function setSortField(field: string) {
    sortField.value = field
    emit('apply:filtered', filteredResults.value)
}

function toggleSortDirection() {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
    emit('apply:filtered', filteredResults.value)
}
</script>

<style scoped>
.search-bar-root {
    width: 100%;
    margin-bottom: 24px;
}

.panel-wrap {
    cursor: text;
}

.filter-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    gap: 12px;
}

.filter-tokens-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    flex-wrap: wrap;
}

.filter-token-group {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    position: relative;
    padding: 1px 2px;
    border-radius: 6px;
}

.filter-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
}

.filter-input {
    border: none;
    outline: none;
    background: transparent;
    padding: 4px 6px;
    font-size: 13px;
    color: rgba(var(--v-theme-on-surface), 0.87);
    min-width: 160px;
    cursor: text;
}

.filter-input::placeholder {
    color: rgba(var(--v-theme-on-surface), 0.5);
}

.field-selector,
.value-selector,
.initial-input {
    display: flex;
    align-items: center;
    gap: 4px;
}


.token {
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    transition: background-color 120ms ease, color 120ms ease;
    color: rgba(var(--v-theme-on-surface), 0.87);
    line-height: 1;
    display: inline-flex;
    align-items: center;
}

.filter-token-group:hover .token {
    background-color: rgba(var(--v-theme-on-surface), 0.04);
}

.token-value {
    /* slightly darker shade for values */
    color: rgba(var(--v-theme-on-surface), 0.95);
    font-weight: 500;
    position: relative;
    padding-right: 22px; /* space for close icon inside */
}

.token-operator {
    opacity: 0.8;
}

.token-close {
    padding: 0;
    min-width: 18px;
    width: 18px;
    height: 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    position: absolute;
    right: 0;
    top: 50%;
    transform: translateY(-50%);
    border-radius: 4px;
}

/* Action buttons (clear, sort, help) square rounded highlights */
.action-btn {
    padding: 0;
    min-width: 34px;
    width: 34px;
    height: 34px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    transition: background-color 120ms ease, border-color 120ms ease;
    border: 1px solid rgba(var(--v-theme-on-surface), 0.06);
    background: transparent;
}
.action-btn:hover {
    background-color: rgba(var(--v-theme-on-surface), 0.06);
    border-color: rgba(var(--v-theme-on-surface), 0.12);
}
.filter-actions .v-icon {
    font-size: 16px;
}

/* Ensure icons inside action buttons are consistent size (help icon was larger) */
.action-btn .v-icon,
.action-btn .v-icon svg {
    font-size: 16px !important;
    width: 16px !important;
    height: 16px !important;
}

.v-btn {
    cursor: pointer;
}
</style>
