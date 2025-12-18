<script setup lang="ts">
import { computed, inject } from 'vue'
import type { ChipBuilderContext, FilterChip, GroupChip } from './types'
import { CHIP_BUILDER_KEY } from './types'

const props = defineProps<{ group: GroupChip; depth: number; isRoot?: boolean }>()

defineOptions({ name: 'QueryGroupNode' })

const injected = inject<ChipBuilderContext>(CHIP_BUILDER_KEY)
if (!injected) {
  throw new Error('QueryGroupNode must be used inside QueryChipBuilder')
}
const ctx = injected

const groupOpModel = computed({
  get: () => props.group.op,
  set: (value: 'and' | 'or') => ctx.changeGroupOp(props.group.id, value),
})

const isRootGroup = computed(() => Boolean(props.isRoot))

function chipLabel(node: FilterChip | GroupChip): string {
  if (node.kind !== 'filter') {
    return ''
  }
  return `${node.field} ${node.op.replace('_', ' ')} ${formatChipValue(node.value)}`
}

function formatChipValue(raw: string): string {
  const trimmed = (raw ?? '').toString().trim()
  if ((trimmed.startsWith('[') && trimmed.endsWith(']')) || (trimmed.startsWith('{') && trimmed.endsWith('}'))) {
    try {
      const parsed = JSON.parse(trimmed)
      if (Array.isArray(parsed)) {
        return `[${parsed.map((entry) => describeValue(entry)).join(', ')}]`
      }
    } catch {
      return trimmed
    }
  }
  return trimmed
}

function describeValue(value: unknown): string {
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

function handleEditChip(node: FilterChip | GroupChip) {
  if (node.kind !== 'filter') {
    return
  }
  ctx.startEditingChip(node, props.group.id)
}

function handleAddConstraint() {
  ctx.startCreateConstraint(props.group.id)
}

function handleAddGroup(op: 'and' | 'or') {
  ctx.addGroup(props.group.id, op)
}

function handleRemoveGroup() {
  ctx.removeNode(props.group.id)
}

function showCreateComposer(): boolean {
  return ctx.isCreateComposerVisible(props.group.id)
}

function isEditingChip(chipId: number): boolean {
  return ctx.isEditingChip(chipId)
}
</script>

<template>
  <div class="group-node" :class="[`group-depth-${depth}`, { 'group-root': isRootGroup }]">
    <div v-if="!isRootGroup" class="group-header">
      <v-tooltip text="Remove group" location="bottom">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            icon="mdi-delete"
            variant="text"
            size="small"
            v-bind="tooltipProps"
            @click.stop="handleRemoveGroup"
          />
        </template>
      </v-tooltip>
    </div>

    <div class="group-children">
      <template v-for="child in group.children" :key="child.id">
        <template v-if="child.kind === 'filter'">
          <div class="chip-shell">
            <div v-if="isEditingChip(child.id)" class="chip-composer-wrapper chip-composer-inline">
              <v-chip class="composer-chip" variant="outlined" color="primary" size="large">
                <div class="composer-row">
                  <v-autocomplete
                    :ref="ctx.setFieldInputRef"
                    v-model="ctx.builderField.value"
                    :items="ctx.fieldItems.value"
                    :loading="ctx.metadataFieldLoading.value"
                    :error="Boolean(ctx.metadataFieldError.value)"
                    :messages="ctx.metadataFieldError.value ? [ctx.metadataFieldError.value] : undefined"
                    clearable
                    hide-no-data
                    hide-selected
                    hide-details
                    label=""
                    aria-label="Field"
                    variant="plain"
                    class="composer-field"
                    density="comfortable"
                    placeholder="e.g. metadata.sample.batch"
                    @keydown.enter.prevent="ctx.advanceFromField"
                    @keydown.esc.prevent="ctx.handleComposerEscape"
                  />

                  <v-select
                    v-if="ctx.canShowOperator.value"
                    :ref="ctx.setOperatorSelectRef"
                    v-model="ctx.builderOp.value"
                    :items="ctx.effectiveOperatorItems.value"
                    label=""
                    aria-label="Operator"
                    hide-details
                    variant="plain"
                    class="composer-operator"
                    density="comfortable"
                    @keydown.enter.prevent="ctx.advanceFromOperator"
                    @keydown.esc.prevent="ctx.handleComposerEscape"
                  />

                  <template v-if="ctx.canShowValue.value">
                    <v-select
                      v-if="ctx.isArrayField.value"
                      :ref="ctx.setValueInputRef"
                      v-model="ctx.builderArraySelections.value"
                      :items="ctx.builderArrayValueOptions.value"
                      :loading="ctx.builderValueLoading.value"
                      :label="ctx.builderValueLabel.value"
                      item-title="label"
                      item-value="token"
                      multiple
                      chips
                      density="comfortable"
                      variant="plain"
                      hide-details
                      clearable
                      class="composer-value"
                      placeholder="Select values"
                      @keydown.enter.prevent="ctx.advanceFromValue"
                      @keydown.esc.prevent="ctx.handleComposerEscape"
                    />
                    <v-combobox
                      v-else
                      :ref="ctx.setValueInputRef"
                      v-model="ctx.builderValue.value"
                      :items="ctx.builderValueSuggestions.value"
                      :loading="ctx.builderValueLoading.value"
                      label=""
                      :aria-label="ctx.builderValueLabel.value"
                      density="comfortable"
                      variant="plain"
                      hide-selected
                      hide-no-data
                      hide-details
                      clearable
                      class="composer-value"
                      placeholder="Provide a value, JSON, or comma list"
                      @keydown.enter.prevent="ctx.advanceFromValue"
                      @keydown.esc.prevent="ctx.handleComposerEscape"
                    />

                    <div class="composer-actions">
                      <v-tooltip text="Save constraint" location="bottom">
                        <template #activator="{ props: tooltipProps }">
                          <v-btn
                            icon="mdi-check"
                            variant="tonal"
                            color="primary"
                            density="comfortable"
                            v-bind="tooltipProps"
                            :disabled="ctx.isLoading.value || !ctx.canCommitChip.value"
                            @click.stop="ctx.commitChip"
                          />
                        </template>
                      </v-tooltip>
                      <v-tooltip text="Cancel" location="bottom">
                        <template #activator="{ props: tooltipProps }">
                          <v-btn
                            icon="mdi-close"
                            variant="text"
                            density="comfortable"
                            v-bind="tooltipProps"
                            @click.stop="ctx.resetBuilder"
                          />
                        </template>
                      </v-tooltip>
                    </div>
                  </template>
                </div>
              </v-chip>
            </div>
            <v-chip
              v-else
              class="ma-1"
              closable
              variant="flat"
              color="primary"
              role="button"
              tabindex="0"
              @click.stop="handleEditChip(child)"
              @keydown.enter.prevent="handleEditChip(child)"
              @keydown.space.prevent="handleEditChip(child)"
              @click:close="ctx.removeNode(child.id)"
            >
              {{ chipLabel(child) }}
            </v-chip>
          </div>
        </template>
        <template v-else>
          <query-group-node :group="child" :depth="depth + 1" />
        </template>
      </template>

      <div v-if="showCreateComposer()" class="chip-composer-wrapper">
        <v-chip class="composer-chip" variant="outlined" color="primary" size="large">
          <div class="composer-row">
            <v-autocomplete
              :ref="ctx.setFieldInputRef"
              v-model="ctx.builderField.value"
              :items="ctx.fieldItems.value"
              :loading="ctx.metadataFieldLoading.value"
              :error="Boolean(ctx.metadataFieldError.value)"
              :messages="ctx.metadataFieldError.value ? [ctx.metadataFieldError.value] : undefined"
              clearable
              hide-no-data
              hide-selected
              hide-details
              label=""
              aria-label="Field"
              variant="plain"
              class="composer-field"
              density="comfortable"
              placeholder="e.g. metadata.sample.batch"
              @keydown.enter.prevent="ctx.advanceFromField"
              @keydown.esc.prevent="ctx.handleComposerEscape"
            />

            <v-select
              v-if="ctx.canShowOperator.value"
              :ref="ctx.setOperatorSelectRef"
              v-model="ctx.builderOp.value"
              :items="ctx.effectiveOperatorItems.value"
              label=""
              aria-label="Operator"
              hide-details
              variant="plain"
              class="composer-operator"
              density="comfortable"
              @keydown.enter.prevent="ctx.advanceFromOperator"
              @keydown.esc.prevent="ctx.handleComposerEscape"
            />

            <template v-if="ctx.canShowValue.value">
              <v-select
                v-if="ctx.isArrayField.value"
                :ref="ctx.setValueInputRef"
                v-model="ctx.builderArraySelections.value"
                :items="ctx.builderArrayValueOptions.value"
                :loading="ctx.builderValueLoading.value"
                :label="ctx.builderValueLabel.value"
                item-title="label"
                item-value="token"
                multiple
                chips
                density="comfortable"
                variant="plain"
                hide-details
                clearable
                class="composer-value"
                placeholder="Select values"
                @keydown.enter.prevent="ctx.advanceFromValue"
                @keydown.esc.prevent="ctx.handleComposerEscape"
              />
              <v-combobox
                v-else
                :ref="ctx.setValueInputRef"
                v-model="ctx.builderValue.value"
                :items="ctx.builderValueSuggestions.value"
                :loading="ctx.builderValueLoading.value"
                label=""
                :aria-label="ctx.builderValueLabel.value"
                density="comfortable"
                variant="plain"
                hide-selected
                hide-no-data
                hide-details
                clearable
                class="composer-value"
                placeholder="Provide a value, JSON, or comma list"
                @keydown.enter.prevent="ctx.advanceFromValue"
                @keydown.esc.prevent="ctx.handleComposerEscape"
              />

              <div class="composer-actions">
                <v-tooltip text="Save constraint" location="bottom">
                  <template #activator="{ props: tooltipProps }">
                    <v-btn
                      icon="mdi-check"
                      variant="tonal"
                      color="primary"
                      density="comfortable"
                      v-bind="tooltipProps"
                      :disabled="ctx.isLoading.value || !ctx.canCommitChip.value"
                      @click.stop="ctx.commitChip"
                    />
                  </template>
                </v-tooltip>
                <v-tooltip text="Cancel" location="bottom">
                  <template #activator="{ props: tooltipProps }">
                    <v-btn
                      icon="mdi-close"
                      variant="text"
                      density="comfortable"
                      v-bind="tooltipProps"
                      @click.stop="ctx.resetBuilder"
                    />
                  </template>
                </v-tooltip>
              </div>
            </template>
          </div>
        </v-chip>
      </div>
    </div>

    <div class="group-actions">
      <div class="group-actions-left">
        <v-tooltip text="Add Filter Constraint" location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              icon="mdi-plus"
              variant="text"
              size="small"
              v-bind="tooltipProps"
              @click.stop="handleAddConstraint"
            />
          </template>
        </v-tooltip>
        <v-tooltip text="Add Constraint Group with AND semantics" location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              icon="mdi-set-merge"
              variant="text"
              size="small"
              v-bind="tooltipProps"
              @click.stop="handleAddGroup('and')"
            />
          </template>
        </v-tooltip>
        <v-tooltip text="Add Constraint Group with OR semantics" location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              icon="mdi-set-split"
              variant="text"
              size="small"
              v-bind="tooltipProps"
              @click.stop="handleAddGroup('or')"
            />
          </template>
        </v-tooltip>
      </div>
      <v-btn-toggle v-model="groupOpModel" density="compact" color="primary" mandatory variant="outlined" divided size="x-small">
        <v-btn value="and">AND</v-btn>
        <v-btn value="or">OR</v-btn>
      </v-btn-toggle>
    </div>
  </div>
</template>

<style scoped>
.group-node {
  border: 1px solid rgba(var(--v-border-color), 0.4);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  background-color: rgba(var(--v-theme-surface), 0.3);
}

.group-root {
  border-style: solid;
  background-color: transparent;
}

.group-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.group-children {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 32px;
}

.group-actions {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.group-actions-left {
  display: flex;
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
  min-width: 180px;
  flex: 0 0 auto;
}

.composer-field {
  width: 280px;
  max-width: 400px;
}

.composer-value {
  width: 280px;
  max-width: 400px;
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
</style>
