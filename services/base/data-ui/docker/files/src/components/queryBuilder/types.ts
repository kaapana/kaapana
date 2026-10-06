import type { ComponentPublicInstance, ComputedRef, InjectionKey, Ref } from 'vue'
import type { MetadataFieldInfo, QueryOp } from '@/types/domain'

export interface ArrayValueOption {
  token: string
  label: string
}

export interface FieldItem {
  title: string
  value: string
  subtitle?: string
  metadata?: MetadataFieldInfo
}

export interface FilterChip {
  id: number
  kind: 'filter'
  field: string
  op: QueryOp
  value: string
}

export interface GroupChip {
  id: number
  kind: 'group'
  op: 'and' | 'or'
  children: ChipNode[]
}

export type ChipNode = FilterChip | GroupChip

export interface ChipBuilderContext {
  fieldItems: ComputedRef<FieldItem[]>
  metadataFieldLoading: Ref<boolean>
  metadataFieldError: Ref<string | null>
  effectiveOperatorItems: ComputedRef<{ title: string; value: QueryOp }[]>
  isArrayField: ComputedRef<boolean>
  builderField: Ref<string>
  builderOp: Ref<QueryOp>
  builderValue: Ref<string>
  builderArraySelections: Ref<string[]>
  builderArrayValueOptions: Ref<ArrayValueOption[]>
  builderValueSuggestions: Ref<string[]>
  builderValueLoading: Ref<boolean>
  builderValueLabel: ComputedRef<string>
  builderError: Ref<string | null>
  canShowOperator: ComputedRef<boolean>
  canShowValue: ComputedRef<boolean>
  canCommitChip: ComputedRef<boolean>
  isComposerActive: Ref<boolean>
  isEditingExisting: ComputedRef<boolean>
  composerParentGroupId: Ref<number>
  editingChipId: Ref<number | null>
  isLoading: ComputedRef<boolean>
  startEditingChip: (chip: FilterChip, parentGroupId: number) => void
  startCreateConstraint: (parentGroupId: number) => void
  commitChip: () => void
  resetBuilder: () => void
  removeNode: (nodeId: number) => void
  addGroup: (parentGroupId: number, op: 'and' | 'or') => void
  changeGroupOp: (groupId: number, op: 'and' | 'or') => void
  isCreateComposerVisible: (groupId: number) => boolean
  isEditingChip: (chipId: number) => boolean
  handleComposerEscape: (event?: KeyboardEvent) => void
  advanceFromField: () => void
  advanceFromOperator: () => void
  advanceFromValue: () => void
  setFieldInputRef: (instance: ComponentPublicInstance | Element | null) => void
  setOperatorSelectRef: (instance: ComponentPublicInstance | Element | null) => void
  setValueInputRef: (instance: ComponentPublicInstance | Element | null) => void
}

export const CHIP_BUILDER_KEY: InjectionKey<ChipBuilderContext> = Symbol('ChipBuilderContext')

export const OPERATOR_LABELS: Record<QueryOp, string> = {
  eq: 'equals',
  lt: 'is less than',
  lte: 'is at most',
  gt: 'is greater than',
  gte: 'is at least',
  in: 'is one of',
  not_in: 'is none of',
  contains: 'contains',
  not_contains: 'does not contain',
  starts_with: 'starts with',
  ends_with: 'ends with',
}
