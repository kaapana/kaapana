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

const hasAdvanced = computed(() => Boolean(props.advancedRows && props.advancedRows.length > 0))
</script>

<template>
  <section>
    <div class="section-title">About</div>
    <div class="source-details-grid">
      <template v-for="row in props.rows" :key="row.label">
        <div class="source-details-label">{{ row.label }}</div>
        <div class="source-details-value">{{ row.value }}</div>
      </template>
      <template v-if="showMore && props.advancedRows">
        <template v-for="row in props.advancedRows" :key="row.label">
          <div class="source-details-label">{{ row.label }}</div>
          <div class="source-details-value">{{ row.value }}</div>
        </template>
      </template>
    </div>
    <v-btn
      v-if="hasAdvanced"
      variant="text"
      size="small"
      class="source-details-toggle"
      @click="showMore = !showMore"
    >
      {{ showMore ? 'Show less' : 'Show more' }}
    </v-btn>
  </section>
</template>

<style scoped>
.section-title {
  font-weight: 500;
  margin-bottom: 8px;
}

.source-details-grid {
  display: grid;
  grid-template-columns: 120px 1fr;
  row-gap: 6px;
  column-gap: 12px;
}

.source-details-label {
  opacity: 0.6;
  font-size: 13px;
}

.source-details-value {
  font-size: 13px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-details-toggle {
  margin-top: 4px;
  margin-left: -8px;
}
</style>
