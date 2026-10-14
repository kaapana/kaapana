<template>
  <div class="d-flex flex-wrap ga-1">
    <v-chip
      v-for="item in sortedItems"
      :key="item"
      size="x-small"
      variant="flat"
      :style="tagChipStyle(item)"
    >
      {{ item }}
    </v-chip>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { tagChipStyle } from '@/utils/tagColors'

const props = withDefaults(defineProps<{ items?: string[] }>(), {
  items: () => [],
})

const sortedItems = computed(() => [...props.items].sort())
</script>
