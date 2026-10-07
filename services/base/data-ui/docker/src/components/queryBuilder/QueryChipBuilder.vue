<script setup lang="ts">
import { computed, nextTick, onMounted, provide, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import type { MetadataFieldInfo, QueryNode, QueryOp } from '@/types/domain'
import { fetchMetadataFieldValues, listMetadataFields, listMetadataSchemas } from '@/services/api'
import QueryGroupNode from './QueryGroupNode.vue'
import {
  CHIP_BUILDER_KEY,
  type ArrayValueOption,
  type ChipBuilderContext,
  type FieldItem,
  type FilterChip,
  type GroupChip,
} from './types'

const props = defineProps<{ loading: boolean }>()
const emit = defineEmits<{ (e: 'run', payload: QueryNode): void; (e: 'clear'): void }>()

const baseFieldItems: FieldItem[] = [
  { title: 'Entity ID', value: 'id', subtitle: 'Text operators' },
  { title: 'Has storage coordinate', value: 'storage.any', subtitle: 'True when any storage entry exists' },
  { title: 'Storage type', value: 'storage.type', subtitle: 'Matches any coordinate type (e.g. s3)' },
]

const metadataFieldInfos = ref<MetadataFieldInfo[]>([])
const metadataFieldLoading = ref(false)
const metadataFieldError = ref<string | null>(null)

const metadataFieldLookup = computed<Record<string, MetadataFieldInfo>>(() => {
  const map: Record<string, MetadataFieldInfo> = {}
  metadataFieldInfos.value.forEach((info) => {
    map[info.field] = info
  })
  return map
})

function buildMetadataSubtitle(info: MetadataFieldInfo): string | undefined {
  const parts: string[] = []
  if (info.value_type) {
    parts.push(`Type: ${info.value_type}`)
  }
  if (info.occurrences) {
    parts.push(`Seen in ${info.occurrences} samples`)
  }
  return parts.length ? parts.join(' · ') : undefined
}

const metadataFieldItems = computed<FieldItem[]>(() =>
  metadataFieldInfos.value.map((info) => ({
    title: `Metadata · ${info.key}${info.path ? `.${info.path}` : ''}`,
    value: info.field,
    subtitle: buildMetadataSubtitle(info),
    metadata: info,
  })),
)

const fieldItems = computed<FieldItem[]>(() => [...baseFieldItems, ...metadataFieldItems.value])

async function loadMetadataFieldHints() {
  metadataFieldLoading.value = true
  metadataFieldError.value = null
  try {
    const keys = await listMetadataSchemas()
    if (!keys.length) {
      metadataFieldInfos.value = []
      return
    }
    const responses = await Promise.allSettled(keys.map((key) => listMetadataFields(key)))
    const aggregated: MetadataFieldInfo[] = []
    responses.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        aggregated.push(...result.value.fields)
      } else {
        console.warn('Failed to load metadata fields for key', keys[index], result.reason)
      }
    })
    const unique = new Map<string, MetadataFieldInfo>()
    aggregated.forEach((field) => {
      unique.set(field.field, field)
    })
    metadataFieldInfos.value = Array.from(unique.values()).sort((a, b) => a.field.localeCompare(b.field))
  } catch (error) {
    metadataFieldError.value = error instanceof Error ? error.message : 'Failed to load metadata field hints'
  } finally {
    metadataFieldLoading.value = false
  }
}

const PREVIEW_OPERATORS: QueryOp[] = ['eq', 'in', 'contains', 'not_contains', 'starts_with', 'ends_with']
const builderValueSuggestions = ref<string[]>([])
const builderArrayValueOptions = ref<ArrayValueOption[]>([])
const builderArraySelections = ref<string[]>([])
const builderValueLoading = ref(false)
const fieldValueCache = new Map<string, string[]>()
const arrayValueOptionCache = new Map<string, ArrayValueOption[]>()

onMounted(() => {
  void loadMetadataFieldHints()
})

const rootGroup = ref<GroupChip>({ id: 0, kind: 'group', op: 'and', children: [] })
const builderField = ref('')
const builderOp = ref<QueryOp>('eq')
const builderValue = ref('')
const builderError = ref<string | null>(null)
const editingChipId = ref<number | null>(null)
const editingParentGroupId = ref<number | null>(null)
const composerParentGroupId = ref(rootGroup.value.id)
const chipCounter = ref(0)
const isComposerActive = ref(false)
const isEditingExisting = computed(() => isComposerActive.value && editingChipId.value !== null)
const preserveValueOnFieldChange = ref(false)
const isLoading = computed(() => props.loading)

function nextChipId(): number {
  chipCounter.value += 1
  return chipCounter.value
}

type FocusableComponent = ComponentPublicInstance | Element
const fieldInputRef = ref<FocusableComponent | null>(null)
const operatorSelectRef = ref<FocusableComponent | null>(null)
const valueInputRef = ref<FocusableComponent | null>(null)

function addGroup(parentGroupId: number, op: 'and' | 'or') {
  const parent = findGroupById(parentGroupId)
  if (!parent) {
    return
  }
  const group: GroupChip = {
    id: nextChipId(),
    kind: 'group',
    op,
    children: [],
  }
  parent.children.push(group)
  emitCurrentQuery()
}

function changeGroupOp(groupId: number, op: 'and' | 'or') {
  const group = findGroupById(groupId)
  if (!group || group.op === op) {
    return
  }
  group.op = op
  emitCurrentQuery()
}

function isCreateComposerVisible(groupId: number): boolean {
  return isComposerActive.value && !isEditingExisting.value && composerParentGroupId.value === groupId
}

function isEditingChip(chipId: number): boolean {
  return isEditingExisting.value && editingChipId.value === chipId
}

const baseOperatorItems: { title: string; value: QueryOp }[] = [
  { title: 'Equals', value: 'eq' },
  { title: 'Contains', value: 'contains' },
  { title: 'Starts with', value: 'starts_with' },
  { title: 'Ends with', value: 'ends_with' },
  { title: 'Not contains', value: 'not_contains' },
  { title: 'Less than', value: 'lt' },
  { title: 'Less or equal', value: 'lte' },
  { title: 'Greater than', value: 'gt' },
  { title: 'Greater or equal', value: 'gte' },
  { title: 'In list', value: 'in' },
  { title: 'Not in list', value: 'not_in' },
]

const booleanOperatorItems: { title: string; value: QueryOp }[] = [
  { title: 'Is', value: 'eq' },
  { title: 'Is not', value: 'not_in' },
]

const arrayOperatorItems: { title: string; value: QueryOp }[] = [
  { title: 'Includes', value: 'contains' },
  { title: 'Not includes', value: 'not_contains' },
]

const builderFieldInfo = computed(() => {
  const field = (builderField.value ?? '').trim()
  return field ? metadataFieldLookup.value[field] : undefined
})

const hasFieldSelection = computed(() => (builderField.value ?? '').trim().length > 0)
const isArrayField = computed(() => builderFieldInfo.value?.value_type === 'array')
const effectiveOperatorItems = computed(() => {
  const info = builderFieldInfo.value
  if (info?.value_type === 'array') {
    return arrayOperatorItems
  }
  if (info?.value_type === 'boolean') {
    return booleanOperatorItems
  }
  return baseOperatorItems
})
const canShowOperator = hasFieldSelection
const canShowValue = computed(() => canShowOperator.value && Boolean(builderOp.value))
const canCommitChip = computed(() => {
  if (!hasFieldSelection.value) {
    return false
  }
  if (isArrayField.value) {
    return builderArraySelections.value.length > 0
  }
  return (builderValue.value ?? '').trim().length > 0
})

function focusComponent(refTarget: typeof fieldInputRef | typeof operatorSelectRef | typeof valueInputRef) {
  if (!isComposerActive.value) {
    return
  }
  nextTick(() => {
    const target = refTarget.value
    if (!target) {
      return
    }
    if (target instanceof HTMLElement || target instanceof SVGElement) {
      target.focus?.()
      return
    }
    const component = target as ComponentPublicInstance & { focus?: () => void; $el?: Element }
    if (typeof component.focus === 'function') {
      component.focus()
      return
    }
    const inputEl = component.$el?.querySelector?.('input, textarea') as HTMLInputElement | HTMLTextAreaElement | null
    inputEl?.focus()
  })
}

function setFieldInputRef(instance: Element | ComponentPublicInstance | null) {
  fieldInputRef.value = instance
}

function setOperatorSelectRef(instance: Element | ComponentPublicInstance | null) {
  operatorSelectRef.value = instance
}

function setValueInputRef(instance: Element | ComponentPublicInstance | null) {
  valueInputRef.value = instance
}

function focusFieldInput() {
  focusComponent(fieldInputRef)
}

function focusOperatorInput() {
  focusComponent(operatorSelectRef)
}

function focusValueInput() {
  if (isArrayField.value) {
    return
  }
  focusComponent(valueInputRef)
}

function advanceFromField() {
  const normalized = (builderField.value ?? '').trim()
  if (!normalized) {
    return
  }
  focusOperatorInput()
}

function advanceFromOperator() {
  if (!builderOp.value) {
    return
  }
  focusValueInput()
}

function advanceFromValue() {
  void commitChip()
}

function handleComposerEscape(event?: KeyboardEvent) {
  if (!isComposerActive.value) {
    return
  }
  event?.preventDefault()
  resetBuilder()
}

function resetBuilderState() {
  builderField.value = ''
  builderOp.value = 'eq'
  builderValue.value = ''
  builderArraySelections.value = []
  builderArrayValueOptions.value = []
  builderError.value = null
  editingChipId.value = null
  editingParentGroupId.value = null
  preserveValueOnFieldChange.value = false
  composerParentGroupId.value = rootGroup.value.id
}

function startCreateConstraint(parentGroupId: number) {
  resetBuilderState()
  composerParentGroupId.value = parentGroupId
  editingParentGroupId.value = parentGroupId
  isComposerActive.value = true
  focusFieldInput()
}

watch(builderField, (next) => {
  builderError.value = null
  const field = (next ?? '').trim()
  if (!field) {
    builderOp.value = 'eq'
    builderValue.value = ''
    builderValueSuggestions.value = []
    builderArraySelections.value = []
    builderArrayValueOptions.value = []
    builderValueLoading.value = false
    editingChipId.value = null
    preserveValueOnFieldChange.value = false
    return
  }
  builderOp.value = builderOp.value ?? 'eq'
  if (preserveValueOnFieldChange.value) {
    preserveValueOnFieldChange.value = false
  } else {
    builderValue.value = ''
    builderArraySelections.value = []
  }
  const info = builderFieldInfo.value
  if (info?.value_type === 'boolean') {
    builderValueSuggestions.value = ['true', 'false']
    builderValueLoading.value = false
    builderArrayValueOptions.value = []
  } else if (info?.value_type === 'array') {
    if (!['contains', 'not_contains'].includes(builderOp.value)) {
      builderOp.value = 'contains'
    }
    builderValueSuggestions.value = []
    builderArrayValueOptions.value = []
    void maybeLoadBuilderValueSuggestions(field, builderOp.value)
  } else {
    builderArrayValueOptions.value = []
    void maybeLoadBuilderValueSuggestions(field, builderOp.value)
  }
  focusOperatorInput()
})

watch(builderOp, (next) => {
  const field = (builderField.value ?? '').trim()
  if (!field) {
    return
  }
  builderError.value = null
  void maybeLoadBuilderValueSuggestions(field, next)
})

watch(builderValue, (next) => {
  if (isArrayField.value) {
    return
  }
  const normalized = (next ?? '').toString().trim()
  if (builderError.value && normalized.length > 0) {
    builderError.value = null
  }
})

watch(builderArraySelections, (next) => {
  if (builderError.value && next.length > 0) {
    builderError.value = null
  }
})

async function maybeLoadBuilderValueSuggestions(field: string, op: QueryOp) {
  const parsed = parseMetadataField(field)
  const info = metadataFieldLookup.value[field]
  const arrayField = info?.value_type === 'array'
  if (!parsed) {
    builderValueSuggestions.value = []
    builderArrayValueOptions.value = []
    builderValueLoading.value = false
    return
  }
  if (!arrayField && !PREVIEW_OPERATORS.includes(op)) {
    builderValueSuggestions.value = []
    builderValueLoading.value = false
    return
  }
  const cacheKey = `${parsed.key}::${parsed.path}`
  if (arrayField) {
    if (arrayValueOptionCache.has(cacheKey)) {
      builderArrayValueOptions.value = arrayValueOptionCache.get(cacheKey) ?? []
      return
    }
  } else if (fieldValueCache.has(cacheKey)) {
    builderValueSuggestions.value = fieldValueCache.get(cacheKey) ?? []
    return
  }
  builderValueLoading.value = true
  try {
    const response = await fetchMetadataFieldValues(parsed.key, parsed.path)
    if (arrayField) {
      const options = extractArrayValueOptions(response.values)
      arrayValueOptionCache.set(cacheKey, options)
      builderArrayValueOptions.value = options
      ensureArrayOptionsFromValues(materializeArraySelectionValues())
    } else {
      const values = response.values.map(formatSampleValue)
      fieldValueCache.set(cacheKey, values)
      builderValueSuggestions.value = values
    }
  } catch (error) {
    console.warn('Failed to load metadata value samples', error)
    if (arrayField) {
      builderArrayValueOptions.value = []
    } else {
      builderValueSuggestions.value = []
    }
  } finally {
    builderValueLoading.value = false
  }
}

function parseMetadataField(field: string): { key: string; path: string } | null {
  const trimmed = field.trim()
  if (!trimmed.startsWith('metadata.')) {
    return null
  }
  const [, key, ...rest] = trimmed.split('.')
  if (!key) {
    return null
  }
  if (!rest.length) {
    return null
  }
  return { key, path: rest.join('.') }
}

function formatSampleValue(value: unknown): string {
  if (value === null || value === undefined) {
    return 'null'
  }
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return JSON.stringify(value)
}

function encodeValueToken(value: unknown): string {
  try {
    return JSON.stringify(value)
  } catch (error) {
    console.warn('Failed to serialize metadata sample value', error)
    return String(value)
  }
}

function decodeValueToken(token: string): unknown {
  try {
    return JSON.parse(token)
  } catch {
    return token
  }
}

function ensureArrayOptionsFromValues(values: unknown[]) {
  if (!values.length) {
    return
  }
  const existing = new Map(builderArrayValueOptions.value.map((option) => [option.token, option]))
  const next = [...builderArrayValueOptions.value]
  values.forEach((value) => {
    const token = encodeValueToken(value)
    if (!existing.has(token)) {
      const entry = { token, label: formatSampleValue(value) }
      existing.set(token, entry)
      next.push(entry)
    }
  })
  builderArrayValueOptions.value = next
}

function extractArrayValueOptions(samples: unknown[]): ArrayValueOption[] {
  const seen = new Set<string>()
  const options: ArrayValueOption[] = []
  const addValue = (value: unknown) => {
    const token = encodeValueToken(value)
    if (seen.has(token)) {
      return
    }
    seen.add(token)
    options.push({ token, label: formatSampleValue(value) })
  }
  samples.forEach((sample) => {
    if (Array.isArray(sample)) {
      sample.forEach(addValue)
    } else {
      addValue(sample)
    }
  })
  return options
}

function materializeArraySelectionValues(): unknown[] {
  return builderArraySelections.value.map((token) => decodeValueToken(token))
}

function hydrateArraySelectionsFromSerializedValue(serialized: string) {
  try {
    const parsed = JSON.parse(serialized)
    const values = Array.isArray(parsed) ? parsed : [parsed]
    builderArraySelections.value = values.map((value) => encodeValueToken(value))
    ensureArrayOptionsFromValues(values)
  } catch {
    builderArraySelections.value = []
  }
}

function findGroupById(groupId: number, current: GroupChip = rootGroup.value): GroupChip | null {
  if (current.id === groupId) {
    return current
  }
  for (const child of current.children) {
    if (child.kind === 'group') {
      const match = findGroupById(groupId, child)
      if (match) {
        return match
      }
    }
  }
  return null
}

function removeNode(nodeId: number, current: GroupChip = rootGroup.value): boolean {
  const index = current.children.findIndex((child) => child.id === nodeId)
  if (index !== -1) {
    current.children.splice(index, 1)
    if (editingChipId.value === nodeId) {
      resetBuilder()
    }
    emitCurrentQuery()
    return true
  }
  for (const child of current.children) {
    if (child.kind === 'group') {
      const removed = removeNode(nodeId, child)
      if (removed) {
        return true
      }
    }
  }
  return false
}

function startEditingChip(chip: FilterChip, parentGroupId: number) {
  isComposerActive.value = true
  preserveValueOnFieldChange.value = true
  composerParentGroupId.value = parentGroupId
  editingParentGroupId.value = parentGroupId
  builderField.value = chip.field
  builderOp.value = chip.op
  builderValue.value = chip.value
  if (metadataFieldLookup.value[chip.field]?.value_type === 'array') {
    hydrateArraySelectionsFromSerializedValue(chip.value)
  } else {
    builderArraySelections.value = []
  }
  editingChipId.value = chip.id
  builderError.value = null
  void maybeLoadBuilderValueSuggestions(chip.field, chip.op)
  if (chip.field) {
    focusOperatorInput()
    focusValueInput()
  }
}

function resetBuilder() {
  resetBuilderState()
  isComposerActive.value = false
}

function commitChip(): boolean {
  const field = (builderField.value ?? '').trim()
  if (!field) {
    builderError.value = 'Select a field'
    return false
  }
  let value = (builderValue.value ?? '').toString().trim()
  if (isArrayField.value) {
    if (!builderArraySelections.value.length) {
      builderError.value = 'Select at least one list item'
      return false
    }
    value = JSON.stringify(materializeArraySelectionValues())
  } else if (!value) {
    builderError.value = 'Provide a value'
    return false
  }
  const parentGroupId = editingChipId.value ? editingParentGroupId.value : composerParentGroupId.value
  const parentGroup = parentGroupId !== null ? findGroupById(parentGroupId) : null
  if (!parentGroup) {
    builderError.value = 'Unable to locate group for constraint'
    return false
  }
  const payload: FilterChip = {
    id: editingChipId.value ?? nextChipId(),
    kind: 'filter',
    field,
    op: builderOp.value,
    value,
  }
  const existingIndex = parentGroup.children.findIndex((child) => child.id === payload.id)
  if (existingIndex >= 0) {
    parentGroup.children.splice(existingIndex, 1, payload)
  } else {
    parentGroup.children.push(payload)
  }
  resetBuilder()
  emitCurrentQuery()
  return true
}

function coerceValue(raw: string): unknown {
  const trimmed = raw.trim()
  if (!trimmed) {
    return ''
  }
  if (trimmed === 'true' || trimmed === 'false') {
    return trimmed === 'true'
  }
  const numberValue = Number(trimmed)
  if (!Number.isNaN(numberValue) && trimmed === numberValue.toString()) {
    return numberValue
  }
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    try {
      return JSON.parse(trimmed)
    } catch (error) {
      console.warn('Failed to parse JSON value', error)
    }
  }
  if (trimmed.includes(',') && !trimmed.includes(' ')) {
    return trimmed.split(',').map((segment) => segment.trim())
  }
  return trimmed
}

function buildNodeFromFilter(chip: FilterChip): QueryNode {
  const rawValue = coerceValue(chip.value)
  const coercedValue = ['in', 'not_in'].includes(chip.op)
    ? Array.isArray(rawValue)
      ? rawValue
      : [rawValue]
    : rawValue
  return {
    type: 'filter',
    field: chip.field,
    op: chip.op,
    value: coercedValue,
  }
}

function emitCurrentQuery() {
  const payload = buildQueryFromGroup(rootGroup.value)
  if (!payload) {
    emit('clear')
    return
  }
  emit('run', payload)
}

function buildQueryFromGroup(group: GroupChip): QueryNode | null {
  const childNodes: QueryNode[] = []
  for (const child of group.children) {
    if (child.kind === 'filter') {
      childNodes.push(buildNodeFromFilter(child))
    } else {
      const nested = buildQueryFromGroup(child)
      if (nested) {
        childNodes.push(nested)
      }
    }
  }
  if (!childNodes.length) {
    return null
  }
  if (childNodes.length === 1 && group.id === rootGroup.value.id) {
    return childNodes[0]!
  }
  return {
    type: 'group',
    op: group.op,
    children: childNodes,
  }
}

function clearAll(options: { emitEvent?: boolean } = {}) {
  const { emitEvent = true } = options
  rootGroup.value.children = []
  resetBuilder()
  if (emitEvent) {
    emit('clear')
  }
}

function startNewConstraint(groupId?: number) {
  startCreateConstraint(groupId ?? rootGroup.value.id)
}

const builderValueLabel = computed(() => {
  const info = builderFieldInfo.value
  if (!info) {
    return 'Value'
  }
  if (info.value_type === 'array') {
    return 'List items'
  }
  const parts: string[] = []
  if (info.value_type) {
    parts.push(`Type: ${info.value_type}`)
  }
  if (info.example !== undefined && info.example !== null) {
    parts.push(`e.g. ${formatSampleValue(info.example)}`)
  }
  return parts.length ? `Value (${parts.join(' · ')})` : 'Value'
})

function stringifyFilterValue(value: unknown): string {
  if (value === null) {
    return 'null'
  }
  if (Array.isArray(value) || typeof value === 'object') {
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return ''
    }
  }
  return value === undefined ? '' : String(value)
}

function chipFromQueryNode(node: QueryNode): FilterChip | GroupChip {
  if (node.type === 'filter') {
    return {
      id: nextChipId(),
      kind: 'filter',
      field: node.field,
      op: node.op,
      value: stringifyFilterValue(node.value),
    }
  }
  return {
    id: nextChipId(),
    kind: 'group',
    op: node.op,
    children: node.children.map((child) => chipFromQueryNode(child)),
  }
}

function loadFromQuery(node: QueryNode | null, options: { emitEvent?: boolean } = {}) {
  const { emitEvent = false } = options
  rootGroup.value.children = []
  rootGroup.value.op = 'and'
  chipCounter.value = 0
  resetBuilder()
  if (!node) {
    if (emitEvent) {
      emit('clear')
    }
    return
  }
  const mapped = chipFromQueryNode(node)
  if (mapped.kind === 'group') {
    rootGroup.value.op = mapped.op
    rootGroup.value.children = mapped.children
  } else {
    rootGroup.value.children = [mapped]
  }
  if (emitEvent) {
    const payload = buildQueryFromGroup(rootGroup.value)
    if (payload) {
      emit('run', payload)
    }
  }
}

function exportQuery(): QueryNode | null {
  return buildQueryFromGroup(rootGroup.value)
}

const builderContext: ChipBuilderContext = {
  fieldItems,
  metadataFieldLoading,
  metadataFieldError,
  effectiveOperatorItems,
  isArrayField,
  builderField,
  builderOp,
  builderValue,
  builderArraySelections,
  builderArrayValueOptions,
  builderValueSuggestions,
  builderValueLoading,
  builderValueLabel,
  builderError,
  canShowOperator,
  canShowValue,
  canCommitChip,
  isComposerActive,
  isEditingExisting,
  composerParentGroupId,
  editingChipId,
  isLoading,
  startEditingChip,
  startCreateConstraint,
  commitChip,
  resetBuilder,
  removeNode,
  addGroup,
  changeGroupOp,
  isCreateComposerVisible,
  isEditingChip,
  handleComposerEscape,
  advanceFromField,
  advanceFromOperator,
  advanceFromValue,
  setFieldInputRef,
  setOperatorSelectRef,
  setValueInputRef,
}

provide(CHIP_BUILDER_KEY, builderContext)

defineExpose({
  clearAll,
  startNewConstraint,
  loadFromQuery,
  exportQuery,
})
</script>

<template>
  <div class="chip-builder">
    <query-group-node :group="rootGroup" :depth="0" :is-root="true" />

    <v-alert v-if="builderError" type="error" density="compact" class="mt-2">
      {{ builderError }}
    </v-alert>
  </div>
</template>

<style scoped>
.chip-builder {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chip-input {
  min-height: 56px;
  border: 1px solid rgba(var(--v-border-color), 0.7);
  border-radius: 12px;
  padding: 8px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.chip-shell {
  display: contents;
}

.chip-composer-wrapper {
  flex: 1;
  min-width: 200px;
}

.chip-composer-inline {
  min-width: auto;
  flex: 0 0 auto;
}

.composer-chip {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  padding: 2px 6px;
  gap: 6px;
  width: auto;
  max-width: 100%;
}

.composer-row {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.composer-field,
.composer-operator,
.composer-value {
  min-width: 140px;
  flex: 0 0 auto;
}

.composer-field {
  width: 210px;
}

.composer-value {
  width: 220px;
}

.composer-field :deep(.v-field__input),
.composer-field :deep(input) {
  white-space: normal;
  word-break: break-word;
}

.composer-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.builder-group {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
