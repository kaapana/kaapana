<script setup lang="ts">
import { computed, inject } from 'vue'
import { icons } from '@/utils/icons'
import QueryConditionComposer from './QueryConditionComposer.vue'
import type { ChipBuilderContext, FilterChip, GroupChip } from './types'
import { CHIP_BUILDER_KEY, OPERATOR_LABELS } from './types'

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
  return `${node.field} ${OPERATOR_LABELS[node.op] ?? node.op} ${formatChipValue(node.value)}`
}

function formatChipValue(raw: string): string {
  const trimmed = (raw ?? '').toString().trim()
  if (
    (trimmed.startsWith('[') && trimmed.endsWith(']')) ||
    (trimmed.startsWith('{') && trimmed.endsWith('}'))
  ) {
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
  <div
    class="group-node rounded pa-3"
    :class="{ border: !isRootGroup, 'bg-surface-light': !isRootGroup }"
    :data-testid="isRootGroup ? 'filter-root' : 'filter-group'"
  >
    <div class="d-flex align-center flex-wrap ga-2 mb-2">
      <span class="text-body-2 text-medium-emphasis">
        {{ isRootGroup ? 'Entities matching' : 'Group matching' }}
      </span>
      <v-btn-toggle
        v-model="groupOpModel"
        density="compact"
        color="primary"
        mandatory
        variant="outlined"
        divided
        :aria-label="isRootGroup ? 'Combine the conditions' : 'Combine the conditions of the group'"
      >
        <v-btn value="and" size="small">all</v-btn>
        <v-btn value="or" size="small">any</v-btn>
      </v-btn-toggle>
      <span class="text-body-2 text-medium-emphasis mr-auto">of these conditions</span>
      <v-btn
        v-if="!isRootGroup"
        :icon="icons.delete"
        variant="text"
        size="small"
        aria-label="Remove group"
        @click.stop="handleRemoveGroup"
      />
    </div>

    <div class="group-children">
      <template v-for="child in group.children" :key="child.id">
        <template v-if="child.kind === 'filter'">
          <QueryConditionComposer v-if="isEditingChip(child.id)" />
          <v-chip
            v-else
            closable
            color="primary"
            :close-label="`Remove condition ${chipLabel(child)}`"
            :aria-label="`Edit condition ${chipLabel(child)}`"
            role="button"
            tabindex="0"
            data-testid="condition"
            @click.stop="handleEditChip(child)"
            @keydown.enter.prevent="handleEditChip(child)"
            @keydown.space.prevent="handleEditChip(child)"
            @click:close="ctx.removeNode(child.id)"
          >
            {{ chipLabel(child) }}
          </v-chip>
        </template>
        <query-group-node v-else :group="child" :depth="depth + 1" />
      </template>

      <QueryConditionComposer v-if="showCreateComposer()" />
    </div>

    <div class="d-flex flex-wrap ga-2 mt-2">
      <v-btn
        variant="text"
        size="small"
        :prepend-icon="icons.add"
        data-testid="add-condition"
        @click.stop="handleAddConstraint"
      >
        Condition
      </v-btn>
      <v-btn
        variant="text"
        size="small"
        :prepend-icon="icons.addGroupAnd"
        @click.stop="handleAddGroup('and')"
      >
        Group (all)
      </v-btn>
      <v-btn
        variant="text"
        size="small"
        :prepend-icon="icons.addGroupOr"
        @click.stop="handleAddGroup('or')"
      >
        Group (any)
      </v-btn>
    </div>
  </div>
</template>

<style scoped>
.group-children {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.group-children > .group-node {
  width: 100%;
}
</style>
