<template>
  <div>
    <v-chip
      v-for="item in sortedItems"
      :key="item"
      :color="stringToColour(item)"
      :class="[sortedItems.length > 1 ? 'multiple-items' : '']"
      style="margin-left: 1px; margin-right: 1px"
      size="x-small"
      variant="flat"
    >
      {{ item }}
    </v-chip>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { stringToColour } from '@/utils/utils'

const props = withDefaults(defineProps<{ items?: string[] }>(), {
  items: () => [],
})

const sortedItems = computed(() => [...props.items].sort())
</script>

<style scoped>
.multiple-items {
  margin-left: 1px;
  margin-right: 1px;
}
</style>
