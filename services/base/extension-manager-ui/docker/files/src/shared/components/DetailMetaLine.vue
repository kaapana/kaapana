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
  <div class="d-flex flex-wrap ga-2">
    <template v-for="(item, index) in visibleItems" :key="index">
      <span v-if="index > 0" aria-hidden="true">·</span>
      <span>{{ item }}</span>
    </template>
  </div>
</template>
