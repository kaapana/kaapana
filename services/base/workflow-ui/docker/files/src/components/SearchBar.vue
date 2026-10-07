<template>
  <div class="search-bar" role="search" aria-label="Filter workflow runs">
    <div class="search-bar-field" @click="focusInput()">
      <div class="search-bar-tokens">
        <div
          v-for="(filter, index) in filters"
          :key="`${filter.field}${filter.operator}${filter.value}`"
          class="search-token"
          data-testid="filter-token"
        >
          <button
            type="button"
            class="search-token-part"
            :aria-label="`Change the field of filter ${tokenLabel(filter)}`"
            @click.stop="editField(index)"
          >
            {{ fieldLabel(filter.field) }}
          </button>
          <button
            type="button"
            class="search-token-part search-token-operator"
            :aria-label="`Change the operator of filter ${tokenLabel(filter)} to ${otherOperator(filter.operator)}`"
            @click.stop="toggleOperator(index)"
          >
            {{ filter.operator }}
          </button>
          <button
            type="button"
            class="search-token-part search-token-value"
            :aria-label="`Change the value of filter ${tokenLabel(filter)}`"
            @click.stop="editValue(index)"
          >
            {{ filter.value }}
          </button>
          <v-btn
            :icon="kaapanaIcons.close"
            size="x-small"
            variant="text"
            density="comfortable"
            :aria-label="`Remove filter ${tokenLabel(filter)}`"
            @click.stop="removeFilter(index)"
          />
        </div>

        <div v-if="building.field" class="search-token search-token--building">
          <span class="search-token-part">{{ fieldLabel(building.field) }}</span>
          <span v-if="building.operator" class="search-token-operator">{{
            building.operator
          }}</span>
        </div>

        <v-menu
          v-model="menuOpen"
          :close-on-content-click="false"
          location="bottom start"
          :open-on-click="false"
          :activator="inputRef ?? undefined"
          width="300"
        >
          <v-card max-height="360" class="overflow-y-auto">
            <v-list density="compact" :aria-label="listLabel">
              <template v-if="!building.field">
                <v-list-subheader>Filter by</v-list-subheader>
                <v-list-item
                  v-for="field in matchingFields"
                  :key="field.key"
                  :prepend-icon="field.icon"
                  :title="field.label"
                  @click="selectField(field.key)"
                />
                <v-list-item v-if="matchingFields.length === 0">
                  <v-list-item-title class="text-medium-emphasis">
                    No filter field matches. Press Enter to search for the text.
                  </v-list-item-title>
                </v-list-item>
              </template>
              <template v-else-if="!building.operator">
                <v-list-item
                  v-for="operator in RUN_FILTER_OPERATORS"
                  :key="operator.value"
                  :title="operator.value"
                  :subtitle="operator.label"
                  @click="selectOperator(operator.value)"
                />
              </template>
              <template v-else-if="fieldValues.length">
                <v-list-item
                  v-for="value in matchingValues"
                  :key="value"
                  @click="commitValue(value)"
                >
                  <v-chip
                    v-if="building.field === 'status'"
                    :color="statusColor(value)"
                    size="small"
                    variant="outlined"
                  >
                    {{ value }}
                  </v-chip>
                  <v-list-item-title v-else>{{ value }}</v-list-item-title>
                </v-list-item>
                <v-list-item v-if="matchingValues.length === 0">
                  <v-list-item-title class="text-medium-emphasis">
                    No value matches. Press Enter to filter by the typed text.
                  </v-list-item-title>
                </v-list-item>
              </template>
              <v-list-item v-else>
                <v-list-item-title class="text-medium-emphasis"
                  >Type a value and press Enter.</v-list-item-title
                >
              </v-list-item>
            </v-list>
          </v-card>
        </v-menu>

        <input
          ref="inputRef"
          v-model="query"
          class="search-bar-input"
          :placeholder="placeholder"
          :aria-label="inputLabel"
          aria-haspopup="listbox"
          :aria-expanded="menuOpen"
          autocomplete="off"
          @input="menuOpen = true"
          @keydown.enter.prevent="onEnter"
          @keydown.escape="onEscape"
          @keydown.backspace="onBackspace"
          @keydown.down.prevent="focusFirstOption"
        />
      </div>

      <div class="d-flex align-center ga-1 flex-shrink-0">
        <v-btn
          v-if="filters.length > 0 || text"
          :icon="kaapanaIcons.close"
          size="small"
          variant="text"
          aria-label="Clear all filters"
          @click.stop="clearAll"
        />

        <v-menu location="bottom end">
          <template #activator="{ props: menuProps }">
            <v-btn
              v-bind="menuProps"
              size="small"
              variant="text"
              prepend-icon="mdi-sort"
              :aria-label="`Sort runs, currently by ${sortLabel}`"
              @click.stop
            >
              {{ sortLabel }}
            </v-btn>
          </template>
          <v-list density="compact" aria-label="Sort runs">
            <v-list-subheader>Sort by</v-list-subheader>
            <v-list-item
              v-for="option in sortOptions"
              :key="option.field"
              :active="sort.field === option.field"
              :title="option.label"
              @click="emit('update:sort', { ...sort, field: option.field })"
            />
            <v-divider />
            <v-list-item
              :prepend-icon="sort.direction === 'desc' ? 'mdi-arrow-down' : 'mdi-arrow-up'"
              :title="sort.direction === 'desc' ? 'Descending' : 'Ascending'"
              @click="
                emit('update:sort', {
                  ...sort,
                  direction: sort.direction === 'desc' ? 'asc' : 'desc',
                })
              "
            />
          </v-list>
        </v-menu>

        <v-btn
          :icon="kaapanaIcons.help"
          size="small"
          variant="text"
          aria-label="How to filter runs"
          @click.stop="showHelp = true"
        />
      </div>
    </div>

    <v-dialog v-model="showHelp" max-width="600">
      <v-card :elevation="5">
        <v-card-title>Filter workflow runs</v-card-title>
        <v-card-text class="text-body-2">
          <p class="mb-3">
            Select the search field, choose a filter field such as Status, then choose or type a
            value. Text that does not start a filter searches the workflow name, external ID, status
            and run ID.
          </p>
          <ul class="ms-4 mb-3">
            <li>
              Filters on different fields must all match. Several = filters on the same field match
              any of them.
            </li>
            <li>
              != excludes a value. Several != filters on the same field exclude all of them. Select
              the operator of a filter to switch between = and !=.
            </li>
            <li>Dates use YYYY-MM-DD, DD.MM.YYYY or DD.MM.YY.</li>
            <li>
              Select a part of a filter to change it. Backspace in the empty search field removes
              the last filter.
            </li>
            <li>The status counts above the table add or remove a status filter.</li>
          </ul>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" @click="showHelp = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import {
  RUN_FILTER_FIELDS,
  RUN_FILTER_OPERATORS,
  runFilterField,
  runFilterValues,
  type RunFilter,
  type RunFilterOperator,
  type RunSort,
  type RunSortField,
} from '@/utils/runFilters'
import { statusColor } from '@/utils/status'
import type { WorkflowRun } from '@/types/schemas'

// GitLab-style query builder. The parent owns the filters, the free text and
// the sort order; this component only edits them.
const props = defineProps<{
  runs: WorkflowRun[]
  filters: RunFilter[]
  text: string
  sort: RunSort
}>()

const emit = defineEmits<{
  (e: 'update:filters', value: RunFilter[]): void
  (e: 'update:text', value: string): void
  (e: 'update:sort', value: RunSort): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const menuOpen = ref(false)
const showHelp = ref(false)

// The filter being created or changed. `index` is null for a new filter.
const building = ref<{
  field: string | null
  operator: RunFilterOperator | null
  index: number | null
}>({ field: null, operator: null, index: null })
const valueQuery = ref('')

const query = computed({
  get: () => (building.value.field ? valueQuery.value : props.text),
  set: (value: string) => {
    if (building.value.field) valueQuery.value = value
    else emit('update:text', value)
  },
})

const listLabel = computed(() => {
  if (!building.value.field) return 'Filter fields'
  return building.value.operator ? 'Values' : 'Operators'
})

const inputLabel = computed(() => {
  if (!building.value.field) return 'Search or filter workflow runs'
  const field = fieldLabel(building.value.field)
  return building.value.operator ? `Value for ${field}` : `Operator for ${field}`
})

const placeholder = computed(() => {
  if (building.value.field && !building.value.operator) return 'Choose = or !='
  if (building.value.field) {
    return (
      runFilterField(building.value.field)?.placeholder ??
      `Choose or type a ${fieldLabel(building.value.field).toLowerCase()}`
    )
  }
  return props.filters.length ? '' : 'Search or filter runs…'
})

const sortOptions: { field: RunSortField; label: string }[] = [
  { field: 'created_at', label: 'Created' },
  { field: 'status', label: 'Status' },
  { field: 'workflow', label: 'Workflow' },
]
const sortLabel = computed(() => sortOptions.find((o) => o.field === props.sort.field)?.label ?? '')

const matchingFields = computed(() => {
  const q = props.text.trim().toLowerCase()
  return RUN_FILTER_FIELDS.filter(
    (f) => !q || f.label.toLowerCase().includes(q) || f.key.includes(q),
  )
})

const fieldValues = computed(() =>
  building.value.field && building.value.operator
    ? runFilterValues(building.value.field, props.runs)
    : [],
)
const matchingValues = computed(() => {
  const q = valueQuery.value.trim().toLowerCase()
  return fieldValues.value.filter((v) => !q || v.toLowerCase().includes(q))
})

function fieldLabel(key: string) {
  return runFilterField(key)?.label ?? key
}

function tokenLabel(filter: RunFilter) {
  return `${fieldLabel(filter.field)} ${filter.operator} ${filter.value}`
}

function otherOperator(operator: RunFilterOperator): RunFilterOperator {
  return operator === '=' ? '!=' : '='
}

function focusInput(openMenu = true) {
  inputRef.value?.focus()
  menuOpen.value = openMenu
}

function focusFirstOption() {
  menuOpen.value = true
  nextTick(() => {
    document
      .querySelector<HTMLElement>('.v-overlay--active .v-list-item:not(.v-list-item--disabled)')
      ?.focus()
  })
}

function selectField(key: string) {
  building.value = { field: key, operator: null, index: building.value.index }
  valueQuery.value = ''
  if (building.value.index === null) emit('update:text', '')
  focusInput()
}

function selectOperator(operator: RunFilterOperator) {
  building.value = { ...building.value, operator }
  valueQuery.value = ''
  focusInput()
}

function toggleOperator(index: number) {
  const filter = props.filters[index]
  const next = [...props.filters]
  next.splice(index, 1, { ...filter, operator: otherOperator(filter.operator) })
  emit('update:filters', next)
}

function commitValue(value: string) {
  const { field, operator } = building.value
  if (!field || !operator || !value.trim()) return
  const next = [...props.filters]
  const filter = { field, operator, value: value.trim() }
  if (building.value.index !== null) next.splice(building.value.index, 1, filter)
  else next.push(filter)
  emit('update:filters', next)
  resetBuilder()
  // Close the suggestions so the filtered table is visible; typing reopens them.
  focusInput(false)
}

function resetBuilder() {
  building.value = { field: null, operator: null, index: null }
  valueQuery.value = ''
}

function onEnter() {
  if (building.value.field && !building.value.operator) {
    const typed = valueQuery.value.trim().toLowerCase()
    const operator = RUN_FILTER_OPERATORS.find((o) => o.value === typed || o.label === typed)
    if (!typed || operator) selectOperator(operator?.value ?? '=')
    return
  }
  if (building.value.field) {
    commitValue(matchingValues.value.length === 1 ? matchingValues.value[0] : valueQuery.value)
    return
  }
  const q = props.text.trim().toLowerCase()
  const exact = RUN_FILTER_FIELDS.find((f) => f.label.toLowerCase() === q || f.key === q)
  if (exact) selectField(exact.key)
  else menuOpen.value = false
}

function onEscape() {
  if (building.value.field) resetBuilder()
  else menuOpen.value = false
}

function onBackspace() {
  if (query.value) return
  if (building.value.field) {
    resetBuilder()
  } else if (props.filters.length) {
    emit('update:filters', props.filters.slice(0, -1))
  }
}

function editField(index: number) {
  building.value = { field: null, operator: null, index }
  emit('update:text', '')
  focusInput()
}

function editValue(index: number) {
  const filter = props.filters[index]
  building.value = { field: filter.field, operator: filter.operator, index }
  valueQuery.value = filter.value
  focusInput()
}

function removeFilter(index: number) {
  emit(
    'update:filters',
    props.filters.filter((_, i) => i !== index),
  )
  resetBuilder()
}

function clearAll() {
  emit('update:filters', [])
  emit('update:text', '')
  resetBuilder()
}
</script>

<style scoped>
.search-bar-field {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 48px;
  padding: 4px 8px 4px 12px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background-color: rgb(var(--v-theme-surface));
  cursor: text;
}

.search-bar-field:focus-within {
  border-color: rgb(var(--v-theme-primary));
}

.search-bar-tokens {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.search-token {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0 2px;
  border-radius: 8px;
  background-color: rgb(var(--v-theme-surface-light));
}

.search-token-part {
  padding: 4px 6px;
  border-radius: 6px;
  color: inherit;
}

button.search-token-part:hover,
button.search-token-part:focus-visible {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

button.search-token-part:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
}

.search-token-value {
  font-weight: 500;
}

.search-token-operator {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.search-bar-input {
  flex: 1;
  min-width: 180px;
  padding: 4px;
  border: none;
  outline: none;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
}

.search-bar-input::placeholder {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
