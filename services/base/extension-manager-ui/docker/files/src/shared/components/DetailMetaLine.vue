<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  items: (string | number | null | undefined)[]
}>()

const visibleItems = computed(() =>
  props.items.filter(
    (item): item is string | number => item !== null && item !== undefined && item !== '',
  ),
)
</script>

<template>
  <div class="detail-meta-line">
    <template v-for="(item, index) in visibleItems" :key="index">
      <span v-if="index > 0" class="detail-meta-line-separator">·</span>
      <span>{{ item }}</span>
    </template>
  </div>
</template>

<style scoped>
.detail-meta-line {
  display: flex;
  flex-wrap: wrap;
  gap: 0 8px;
}

.detail-meta-line-separator {
  text-align: center;
}
</style>
