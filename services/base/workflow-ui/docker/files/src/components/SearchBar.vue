<template>
  <div
    ref="rootRef"
    class="search-bar"
    role="search"
    :aria-label="`Filter ${name}`"
    @focusout="onFocusOut"
  >
    <div class="search-bar-box">
      <div class="search-bar-field" @click="focusInput()">
        <div class="search-bar-tokens">
          <template v-for="(group, groupIndex) in filterGroups" :key="group[0].index">
            <button
              v-if="groupIndex > 0"
              type="button"
              class="search-connector"
              data-testid="filter-connector"
              :aria-label="`Change AND before filter ${tokenLabel(group[0].filter)} to OR`"
              @click.stop="toggleConnector(group[0].index)"
            >
              AND
            </button>
            <div
              class="search-group"
              :class="{ 'search-group--or': group.length > 1 }"
              data-testid="filter-group"
            >
              <template v-for="({ filter, index }, position) in group" :key="index">
                <button
                  v-if="position > 0"
                  type="button"
                  class="search-connector"
                  data-testid="filter-connector"
                  :aria-label="`Change OR before filter ${tokenLabel(filter)} to AND`"
                  @click.stop="toggleConnector(index)"
                >
                  OR
                </button>
                <div class="search-token" data-testid="filter-token">
                  <button
                    type="button"
                    class="search-token-part"
                    :aria-label="`Change the key of filter ${tokenLabel(filter)}`"
                    @click.stop="editKey(index)"
                  >
                    {{ keyLabel(filter.key) }}
                  </button>
                  <button
                    type="button"
                    class="search-token-part search-token-operator"
                    :aria-label="`Change the operator of filter ${tokenLabel(filter)}`"
                    @click.stop="editOperator(index)"
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
                    @click.stop="removeAt(index)"
                  />
                </div>
              </template>
            </div>
          </template>

          <div v-if="building.key" class="search-token search-token--building">
            <span class="search-token-part">{{ keyLabel(building.key) }}</span>
            <span v-if="building.operator" class="search-token-operator">{{
              building.operator
            }}</span>
          </div>

          <v-menu
            v-model="menuOpen"
            persistent
            :close-on-content-click="false"
            location="bottom start"
            :open-on-click="false"
            :activator="inputRef ?? undefined"
            :width="buildingDate && building.operator ? undefined : 300"
          >
            <v-card ref="menuRef" max-height="480" class="overflow-y-auto">
              <v-date-picker
                v-if="buildingDate && building.operator"
                :model-value="pickedDate"
                hide-header
                show-adjacent-months
                @update:model-value="commitDate"
              />
              <v-list v-else density="compact" :aria-label="listLabel">
                <template v-if="!building.key">
                  <v-list-subheader>Filter by</v-list-subheader>
                  <v-list-item
                    v-for="filterKey in matchingKeys"
                    :key="filterKey.key"
                    :prepend-icon="filterKey.icon"
                    :title="filterKey.label"
                    @click="selectKey(filterKey.key)"
                  />
                  <v-list-item v-if="matchingKeys.length === 0">
                    <v-list-item-title class="text-medium-emphasis">
                      No filter key matches. Press Enter to search for the text.
                    </v-list-item-title>
                  </v-list-item>
                </template>
                <template v-else-if="!building.operator">
                  <v-list-item
                    v-for="operator in keyOperators"
                    :key="operator"
                    :title="operator"
                    :subtitle="FILTER_OPERATOR_LABELS[operator]"
                    @click="selectOperator(operator)"
                  />
                </template>
                <template v-else-if="keyValues.length">
                  <v-list-item
                    v-for="value in matchingValues"
                    :key="value"
                    @click="commitValue(value)"
                  >
                    <v-chip
                      v-if="valueColor?.(building.key, value)"
                      :color="valueColor(building.key, value)"
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

        <v-btn
          v-if="draftFilters.length > 0 || draftText"
          :icon="kaapanaIcons.close"
          size="small"
          variant="text"
          aria-label="Clear all filters"
          @click.stop="clearAll"
        />
      </div>

      <button type="button" class="search-bar-submit" aria-label="Search" @click.stop="submit">
        <v-icon :icon="kaapanaIcons.search" size="small" />
      </button>
    </div>

    <v-menu location="bottom end">
      <template #activator="{ props: menuProps }">
        <v-btn
          v-bind="menuProps"
          variant="text"
          prepend-icon="mdi-sort"
          :aria-label="`Sort ${shortName}, currently by ${sortLabel}`"
        >
          {{ sortLabel }}
        </v-btn>
      </template>
      <v-list density="compact" :aria-label="`Sort ${shortName}`">
        <template v-if="sortOptions.length > 1">
          <v-list-subheader>Sort by</v-list-subheader>
          <v-list-item
            v-for="option in sortOptions"
            :key="option.field"
            :active="sort.field === option.field"
            :title="option.label"
            @click="emit('update:sort', { ...sort, field: option.field })"
          />
          <v-divider />
        </template>
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
      :aria-label="`How to filter ${shortName}`"
      @click.stop="showHelp = true"
    />

    <v-dialog v-model="showHelp" max-width="600">
      <v-card :elevation="5">
        <v-card-title>Filter {{ name }}</v-card-title>
        <v-card-text class="text-body-2">
          <p class="mb-4">
            A filter has a key, an operator and a value, for example
            <code>{{ example }}</code
            >. <slot name="free-text" /> Press Enter or select Search to apply the filters.
          </p>

          <div class="text-subtitle-2 mb-1">Combining filters</div>
          <ul class="ms-4 mb-4">
            <li>
              Between two filters, <strong>AND</strong> (default) means both must match and
              <strong>OR</strong> means either can match. Click the AND or OR to switch.
            </li>
            <li>Filters joined with OR are framed as a group.</li>
          </ul>

          <div class="text-subtitle-2 mb-1">Operators</div>
          <ul class="ms-4 mb-4">
            <li><strong>Equal</strong> (<code>=</code>) keeps the matches.</li>
            <li><strong>Not equal</strong> (<code>!=</code>) excludes them.</li>
            <li v-if="hasDateKeys">Date filters only take <code>=</code>, which is filled in.</li>
          </ul>

          <div class="text-subtitle-2 mb-1">Editing</div>
          <ul class="ms-4">
            <li>
              Select a part of a filter to change it. A new key or operator asks for the value
              again.
            </li>
            <li>Backspace in the empty search field removes the last filter.</li>
            <li v-if="hasDateKeys">Pick a date in the calendar or type it as YYYY-MM-DD.</li>
            <slot name="help" />
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

<script setup lang="ts" generic="F extends string">
import { computed, nextTick, ref, watch } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import {
  ALL_OPERATORS,
  FILTER_OPERATOR_LABELS,
  formatSearchDate,
  groupFilters,
  parseSearchDate,
  removeFilter,
  type Filter,
  type FilterKey,
  type FilterOperator,
  type Sort,
  type SortOption,
} from '@/utils/filters'

const props = defineProps<{
  name: string
  shortName: string
  example: string
  filterKeys: FilterKey[]
  valuesFor: (key: string) => string[]
  valueColor?: (key: string, value: string) => string | undefined
  filters: Filter[]
  text: string
  sort: Sort<F>
  sortOptions: SortOption<F>[]
}>()

const emit = defineEmits<{
  (e: 'update:filters', value: Filter[]): void
  (e: 'update:text', value: string): void
  (e: 'update:sort', value: Sort<F>): void
}>()

const rootRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const menuRef = ref<{ $el: HTMLElement } | null>(null)
const menuOpen = ref(false)
const showHelp = ref(false)

const draftFilters = ref<Filter[]>([])
const draftText = ref('')

watch(
  () => props.filters,
  (filters) => {
    draftFilters.value = filters.map((f) => ({ ...f }))
  },
  { immediate: true },
)
watch(
  () => props.text,
  (text) => {
    draftText.value = text
  },
  { immediate: true },
)

const building = ref<{
  key: string | null
  operator: FilterOperator | null
  index: number | null
}>({ key: null, operator: null, index: null })
const valueQuery = ref('')

const query = computed({
  get: () => (building.value.key ? valueQuery.value : draftText.value),
  set: (value: string) => {
    if (building.value.key) valueQuery.value = value
    else draftText.value = value
  },
})

const filterGroups = computed(() => groupFilters(draftFilters.value))
const hasDateKeys = computed(() => props.filterKeys.some((k) => k.date))

const buildingKey = computed(() => (building.value.key ? findKey(building.value.key) : undefined))
const buildingDate = computed(() => !!buildingKey.value?.date)
const keyOperators = computed(() => buildingKey.value?.operators ?? ALL_OPERATORS)
const pickedDate = computed(() => parseSearchDate(valueQuery.value) ?? undefined)

const listLabel = computed(() => {
  if (!building.value.key) return 'Filter keys'
  return building.value.operator ? 'Values' : 'Operators'
})

const inputLabel = computed(() => {
  if (!building.value.key) return `Search or filter ${props.name}`
  const key = keyLabel(building.value.key)
  return building.value.operator ? `Value for ${key}` : `Operator for ${key}`
})

const placeholder = computed(() => {
  if (building.value.key && !building.value.operator) {
    return `Choose ${keyOperators.value.join(' or ')}`
  }
  if (building.value.key) {
    return (
      buildingKey.value?.placeholder ??
      `Choose or type a ${keyLabel(building.value.key).toLowerCase()}`
    )
  }
  return draftFilters.value.length ? '' : `Search or filter ${props.shortName}…`
})

const sortLabel = computed(
  () => props.sortOptions.find((o) => o.field === props.sort.field)?.label ?? '',
)

const matchingKeys = computed(() => {
  const q = draftText.value.trim().toLowerCase()
  return props.filterKeys.filter(
    (f) => !q || f.label.toLowerCase().includes(q) || f.key.includes(q),
  )
})

const keyValues = computed(() =>
  building.value.key && building.value.operator ? props.valuesFor(building.value.key) : [],
)
const matchingValues = computed(() => {
  const q = valueQuery.value.trim().toLowerCase()
  return keyValues.value.filter((v) => !q || v.toLowerCase().includes(q))
})

function findKey(key: string) {
  return props.filterKeys.find((f) => f.key === key)
}

function keyLabel(key: string) {
  return findKey(key)?.label ?? key
}

function tokenLabel(filter: Filter) {
  return `${keyLabel(filter.key)} ${filter.operator} ${filter.value}`
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

function onlyOperator(key: string): FilterOperator | null {
  const operators = findKey(key)?.operators ?? ALL_OPERATORS
  return operators.length === 1 ? operators[0] : null
}

function selectKey(key: string) {
  building.value = { key, operator: onlyOperator(key), index: building.value.index }
  valueQuery.value = ''
  if (building.value.index === null) draftText.value = ''
  focusInput()
}

function selectOperator(operator: FilterOperator) {
  building.value = { ...building.value, operator }
  valueQuery.value = ''
  focusInput()
}

function toggleConnector(index: number) {
  const filter = draftFilters.value[index]
  const next = [...draftFilters.value]
  next.splice(index, 1, { ...filter, connector: filter.connector === 'or' ? 'and' : 'or' })
  draftFilters.value = next
}

function submit() {
  resetBuilder()
  menuOpen.value = false
  emit(
    'update:filters',
    draftFilters.value.map((f) => ({ ...f })),
  )
  emit('update:text', draftText.value)
}

function commitValue(value: string) {
  const { key, operator, index } = building.value
  if (!key || !operator || !value.trim()) return
  if (buildingDate.value) {
    const date = parseSearchDate(value)
    if (!date) return
    value = formatSearchDate(date)
  }
  const next = [...draftFilters.value]
  const connector = index !== null ? (draftFilters.value[index].connector ?? 'and') : 'and'
  const filter: Filter = { key, operator, value: value.trim(), connector }
  if (index !== null) next.splice(index, 1, filter)
  else next.push(filter)
  draftFilters.value = next
  resetBuilder()
  focusInput()
}

function commitDate(date: unknown) {
  if (date instanceof Date) commitValue(formatSearchDate(date))
}

function resetBuilder() {
  building.value = { key: null, operator: null, index: null }
  valueQuery.value = ''
}

function onEnter() {
  if (building.value.key && !building.value.operator) {
    const typed = valueQuery.value.trim().toLowerCase()
    const operator = keyOperators.value.find(
      (o) => o === typed || FILTER_OPERATOR_LABELS[o] === typed,
    )
    if (!typed || operator) selectOperator(operator ?? keyOperators.value[0])
    return
  }
  if (building.value.key) {
    commitValue(matchingValues.value.length === 1 ? matchingValues.value[0] : valueQuery.value)
    return
  }
  const q = draftText.value.trim().toLowerCase()
  const exact = props.filterKeys.find((f) => f.label.toLowerCase() === q || f.key === q)
  if (exact) selectKey(exact.key)
  else submit()
}

function onFocusOut(event: FocusEvent) {
  const next = event.relatedTarget as Node | null
  if (next && (rootRef.value?.contains(next) || menuRef.value?.$el.contains(next))) return
  resetBuilder()
  menuOpen.value = false
}

function onEscape() {
  resetBuilder()
  menuOpen.value = false
}

function onBackspace() {
  if (query.value) return
  if (building.value.key) {
    resetBuilder()
  } else if (draftFilters.value.length) {
    draftFilters.value = draftFilters.value.slice(0, -1)
    menuOpen.value = true
  }
}

function editKey(index: number) {
  building.value = { key: null, operator: null, index }
  draftText.value = ''
  focusInput()
}

function editOperator(index: number) {
  const key = draftFilters.value[index].key
  building.value = { key, operator: onlyOperator(key), index }
  valueQuery.value = ''
  focusInput()
}

function editValue(index: number) {
  const filter = draftFilters.value[index]
  building.value = { key: filter.key, operator: filter.operator, index }
  valueQuery.value = filter.value
  focusInput()
}

function removeAt(index: number) {
  draftFilters.value = removeFilter(draftFilters.value, index)
  resetBuilder()
  focusInput()
}

function clearAll() {
  draftFilters.value = []
  draftText.value = ''
  resetBuilder()
  emit('update:filters', [])
  emit('update:text', '')
  focusInput()
}
</script>

<style scoped>
.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-bar-box {
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 48px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background-color: rgb(var(--v-theme-surface));
  overflow: hidden;
}

.search-bar-box:focus-within {
  border-color: rgb(var(--v-theme-primary));
}

.search-bar-field {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 4px 4px 4px 12px;
  cursor: text;
}

.search-bar-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  border-left: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.search-bar-submit:hover,
.search-bar-submit:focus-visible {
  background-color: rgba(var(--v-theme-on-surface), 0.06);
  color: rgb(var(--v-theme-on-surface));
}

.search-bar-submit:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -2px;
}

.search-bar-tokens {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.search-group {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.search-group--or {
  padding: 2px 4px;
  border: 1px dashed rgba(var(--v-border-color), 0.5);
  border-radius: 10px;
}

.search-connector {
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: rgb(var(--v-theme-primary));
}

.search-connector:hover,
.search-connector:focus-visible {
  background-color: rgba(var(--v-theme-primary), 0.12);
}

.search-connector:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
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
