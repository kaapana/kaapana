<template>
  <div class="d-flex flex-wrap ga-1">
    <v-chip
      v-for="item in sortedItems"
      :key="item"
      size="x-small"
      variant="flat"
      closable
      :style="chipStyle(item)"
      :close-label="`Remove tag ${item}`"
      @click:close="emit('deleteTag', item)"
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

const emit = defineEmits<{ deleteTag: [tag: string] }>()

const sortedItems = computed(() => [...props.items].sort())

// Vuetify derives a contrasting foreground only for theme tokens, so a literal
// hex background needs its text colour supplied explicitly.
function chipStyle(item: string) {
  const { background, text } = tagColor(item)
  return { backgroundColor: background, color: text }
}
</script>
