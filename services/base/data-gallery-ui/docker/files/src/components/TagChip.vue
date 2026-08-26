<template>
  <div>
    <v-chip
      v-for="item in sortedItems"
      :key="item"
      :color="stringToColour(item)"
      style="margin-left: 1px; margin-right: 1px"
      size="x-small"
      closable
      variant="flat"
      @click:close="emit('deleteTag', item)"
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

const emit = defineEmits<{ deleteTag: [tag: string] }>()

const sortedItems = computed(() => [...props.items].sort())
</script>

<style scoped></style>
