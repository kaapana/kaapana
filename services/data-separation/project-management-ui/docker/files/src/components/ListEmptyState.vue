<template>
  <v-empty-state
    v-if="search"
    :icon="kaapanaIcons.search"
    size="56"
    :title="noMatchTitle"
    text="Change the search or clear it to see the whole list."
  >
    <template #actions>
      <v-btn color="primary" variant="text" @click="emit('clearSearch')">Clear search</v-btn>
    </template>
  </v-empty-state>
  <v-empty-state v-else size="56" :title="title" :text="text">
    <template v-if="$slots.actions" #actions>
      <slot name="actions" />
    </template>
  </v-empty-state>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { kaapanaIcons } from '@/utils/projectIcons'

const props = defineProps<{
  search?: string | null
  /** Plural of what the list holds, for the no-matches title. */
  noun: string
  title: string
  text: string
}>()

const emit = defineEmits<{ (e: 'clearSearch'): void }>()

const noMatchTitle = computed(() => `No ${props.noun} match "${props.search}"`)
</script>
