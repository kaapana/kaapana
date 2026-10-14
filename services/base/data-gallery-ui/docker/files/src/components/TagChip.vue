<template>
  <div class="d-flex flex-wrap ga-1">
    <v-chip
      v-for="item in sortedItems"
      :key="item"
      :model-value="true"
      size="x-small"
      variant="flat"
      closable
      :style="tagChipStyle(item)"
      :close-label="`Remove tag ${item}`"
      @update:model-value="() => {}"
      @click:close="emit('deleteTag', item)"
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

const emit = defineEmits<{ deleteTag: [tag: string] }>()

const sortedItems = computed(() => [...props.items].sort())
</script>
