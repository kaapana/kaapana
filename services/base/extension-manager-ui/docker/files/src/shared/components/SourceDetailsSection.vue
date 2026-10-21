<script setup lang="ts">
import { computed, ref } from 'vue'

export interface SourceDetailsRow {
  label: string
  value: string
}

const props = defineProps<{
  rows: SourceDetailsRow[]
  advancedRows?: SourceDetailsRow[]
}>()

const showMore = ref(false)

const visibleRows = computed(() =>
  showMore.value ? [...props.rows, ...(props.advancedRows ?? [])] : props.rows,
)
const hasAdvanced = computed(() => Boolean(props.advancedRows?.length))
</script>

<template>
  <section>
    <h3 class="text-subtitle-1 mb-2">About</h3>
    <dl class="source-details text-body-2">
      <template v-for="row in visibleRows" :key="row.label">
        <dt class="text-medium-emphasis">{{ row.label }}</dt>
        <dd>{{ row.value }}</dd>
      </template>
    </dl>
    <v-btn
      v-if="hasAdvanced"
      variant="text"
      size="small"
      class="mt-1 ms-n2"
      :aria-expanded="showMore"
      @click="showMore = !showMore"
    >
      {{ showMore ? 'Show less' : 'Show more' }}
    </v-btn>
  </section>
</template>

<style scoped>
.source-details {
  display: grid;
  grid-template-columns: max-content 1fr;
  column-gap: 16px;
  row-gap: 4px;
  margin: 0;
}

.source-details dd {
  margin: 0;
  min-width: 0;
  overflow-wrap: anywhere;
}
</style>
