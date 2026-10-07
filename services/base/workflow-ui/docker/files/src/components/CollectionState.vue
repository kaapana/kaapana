<script setup lang="ts">
import { kaapanaIcons } from '@kaapana/base-ui'

const props = defineProps<{
  state: 'error' | 'no-matches' | 'empty'
  /** Plural name of the collection, for example "workflows". */
  noun: string
  emptyText: string
  errorText?: string
  hasErrorDetails?: boolean
  retrying?: boolean
}>()

defineEmits<{
  (event: 'retry'): void
  (event: 'showDetails'): void
  (event: 'clearFilters'): void
}>()
</script>

<template>
  <div data-testid="collection-state">
    <v-empty-state
      v-if="props.state === 'error'"
      :icon="kaapanaIcons.error"
      color="error"
      size="56"
      :title="`Could not load the ${props.noun}`"
      :text="props.errorText"
    >
      <template #actions>
        <v-btn
          color="primary"
          variant="text"
          :prepend-icon="kaapanaIcons.refresh"
          :loading="props.retrying"
          :disabled="props.retrying"
          @click="$emit('retry')"
        >
          Try again
        </v-btn>
        <v-btn v-if="props.hasErrorDetails" variant="text" @click="$emit('showDetails')">
          Details
        </v-btn>
      </template>
    </v-empty-state>

    <v-empty-state
      v-else-if="props.state === 'no-matches'"
      :icon="kaapanaIcons.search"
      size="56"
      :title="`No ${props.noun} match the current filters`"
      text="Clear the filters to see everything."
    >
      <template #actions>
        <v-btn color="primary" variant="text" @click="$emit('clearFilters')">Clear filters</v-btn>
      </template>
    </v-empty-state>

    <v-empty-state v-else size="56" :title="`No ${props.noun} yet`" :text="props.emptyText">
      <template #actions>
        <slot name="empty-actions" />
      </template>
    </v-empty-state>
  </div>
</template>
