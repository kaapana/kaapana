<script setup lang="ts">
import { ref } from 'vue'
import type { QueryNode } from '@/types/domain'
import QueryChipBuilderInner from '@/components/queryBuilder/QueryChipBuilder.vue'

const props = defineProps<{ loading: boolean }>()
const emit = defineEmits<{ (e: 'run', payload: QueryNode): void; (e: 'clear'): void }>()

type InnerExpose = {
  clearAll: (options?: { emitEvent?: boolean }) => void
  startNewConstraint: (groupId?: number) => void
  loadFromQuery: (node: QueryNode | null, options?: { emitEvent?: boolean }) => void
  exportQuery: () => QueryNode | null
}

const innerRef = ref<InnerExpose | null>(null)

function handleRun(payload: QueryNode) {
  emit('run', payload)
}

function handleClear() {
  emit('clear')
}

function clearAll(options?: { emitEvent?: boolean }) {
  innerRef.value?.clearAll(options)
}

function startNewConstraint(groupId?: number) {
  innerRef.value?.startNewConstraint(groupId)
}

function loadFromQuery(node: QueryNode | null, options?: { emitEvent?: boolean }) {
  innerRef.value?.loadFromQuery(node, options)
}

function exportQuery(): QueryNode | null {
  return innerRef.value?.exportQuery() ?? null
}

defineExpose({
  clearAll,
  startNewConstraint,
  loadFromQuery,
  exportQuery,
})
</script>

<template>
  <QueryChipBuilderInner ref="innerRef" v-bind="props" @run="handleRun" @clear="handleClear" />
</template>
