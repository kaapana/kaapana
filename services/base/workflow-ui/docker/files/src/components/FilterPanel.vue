<template>
  <v-card class="pa-4" elevation="2">
    <v-card-text>
      <!-- SEARCH -->
      <v-text-field 
        v-model="searchQuery" 
        label="Search workflows" 
        prepend-inner-icon="mdi-magnify" 
        density="compact"
        variant="outlined"
        clearable 
        class="mb-4" 
      />

      <!-- Categories -->
      <div class="mb-4">
        <div class="mb-2 text-left text-h6 font-weight-bold d-flex align-center">
          <v-icon class="me-2" size="20">mdi-label-multiple</v-icon>
          Categories
        </div>
        <v-chip-group 
          v-model="selectedCategories" 
          multiple 
          column 
          class="d-flex flex-wrap"
        >
          <v-chip 
            v-for="category in availableCategories" 
            :key="category" 
            :value="category" 
            variant="outlined"
            filter
            class="ma-1"
          >
            {{ category }}
          </v-chip>
        </v-chip-group>
      </div>

      <!-- PROVIDERS -->
      <div class="mb-4">
        <div class="mb-2 text-left text-h6 font-weight-bold d-flex align-center">
          <v-icon class="me-2" size="20">mdi-domain</v-icon>
          Providers
        </div>
        <v-chip-group 
          v-model="selectedProviders" 
          multiple 
          column 
          class="d-flex flex-wrap"
        >
          <v-chip 
            v-for="provider in availableProviders" 
            :key="provider" 
            :value="provider" 
            variant="outlined"
            filter
            class="ma-1"
          >
            {{ provider }}
          </v-chip>
        </v-chip-group>
      </div>

      <!-- RESET -->
      <v-btn color="primary" @click="resetFilters" block>Reset Filters</v-btn>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Workflow } from '@/types/workflow'

// --- PROPS ---
const props = defineProps<{
  workflows: Workflow[]
  filters: {
    search: string
    categories: string[]
    providers: string[]
  }
}>()

const emit = defineEmits<{
  (e: 'update:filters', value: typeof props.filters): void
}>()

// --- LOCAL STATE ---
const searchQuery = ref(props.filters.search)
const selectedCategories = ref<string[]>(props.filters.categories)
const selectedProviders = ref<string[]>(props.filters.providers)

// --- AVAILABLE FILTER OPTIONS ---
const availableCategories = computed(() => {
  const categories = new Set<string>()
  props.workflows.forEach(w => {
    w.labels.forEach(l => {
      if (l.key === 'kaapana-ui.category' && l.value) {
        categories.add(l.value)
      }
    })
  })
  return Array.from(categories).sort()
})

const availableProviders = computed(() => {
  const providers = new Set<string>()
  props.workflows.forEach(w => {
    w.labels.forEach(l => {
      if (l.key === 'kaapana-ui.provider' && l.value) {
        providers.add(l.value)
      }
    })
  })
  return Array.from(providers).sort()
})

// --- EMIT CHANGES ---
watch([searchQuery, selectedCategories, selectedProviders], () => {
  emit('update:filters', {
    search: searchQuery.value || '',
    categories: selectedCategories.value || [],
    providers: selectedProviders.value || [],
  })
}, { deep: true })

// --- RESET ---
function resetFilters() {
  searchQuery.value = ''
  selectedCategories.value = []
  selectedProviders.value = []
}
</script>

<style scoped>
.v-card {
  width: 100%;
}
</style>