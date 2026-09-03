<template>
  <div class="d-flex flex-wrap ga-1">
    <v-chip
      v-for="item in sortedItems"
      :key="item"
      size="x-small"
      variant="flat"
      :style="chipStyle(item)"
    >
      {{ item }}
    </v-chip>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { tagColor } from '@/utils/tagColors'

const props = withDefaults(defineProps<{ items?: string[] }>(), {
  items: () => [],
})

const sortedItems = computed(() => [...props.items].sort())

function chipStyle(item: string) {
  const { background, text } = tagColor(item)
  return { backgroundColor: background, color: text }
}
</script>
