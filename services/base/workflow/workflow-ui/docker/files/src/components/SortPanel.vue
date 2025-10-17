<template>
  <v-select
    v-model="selectedSort"
    :items="sortOptions"
    label="Sort by"
    variant="outlined"
    density="comfortable"
    hide-details
    class="ma-2"
  />
</template>

<script setup lang="ts">
import { ref, watch, defineProps, defineEmits } from 'vue'

const props = defineProps<{
  sortOptions: string[]
  modelValue: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

// internal reactive value synced with parent
const selectedSort = ref(props.modelValue)

// Sync parent <-> child
watch(() => props.modelValue, v => (selectedSort.value = v))
watch(selectedSort, v => emit('update:modelValue', v))
</script>
