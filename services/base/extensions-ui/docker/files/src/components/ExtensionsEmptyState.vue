<script setup lang="ts">
import { kaapanaIcons } from '@/utils/extensionIcons'

// "An empty screen should explain why it is empty." The three states the
// guidelines name are distinct here, and a load failure in particular must not
// be dressed up as an empty collection — which is what Vuetify's default
// "No data available" did for all three.
const props = defineProps<{
  state: 'error' | 'no-matches' | 'empty'
  /** The reason the load failed, when the backend gave one. */
  errorDetail?: string | null
  /** Whether the current user may trigger a catalogue download. */
  canUpdateExtensions?: boolean
  /** A catalogue download is already running. */
  busy?: boolean
  /** A reload triggered from here is already running. */
  retrying?: boolean
}>()

defineEmits<{
  (event: 'retry'): void
  (event: 'clearFilters'): void
  (event: 'updateExtensions'): void
}>()
</script>

<template>
  <div class="extensions-empty-state text-center py-8 px-4" data-testid="extensions-empty-state">
    <template v-if="props.state === 'error'">
      <v-icon :icon="kaapanaIcons.error" color="error" size="x-large" class="mb-3" />
      <div class="text-h6 mb-1">Could not load the extension list</div>
      <div class="text-body-2 text-medium-emphasis mb-4">
        {{ props.errorDetail || 'The extension service did not answer.' }}
      </div>
      <v-btn
        color="primary"
        variant="flat"
        :prepend-icon="kaapanaIcons.refresh"
        :loading="props.retrying"
        :disabled="props.retrying"
        @click="$emit('retry')"
      >
        Try again
      </v-btn>
    </template>

    <template v-else-if="props.state === 'no-matches'">
      <v-icon :icon="kaapanaIcons.search" size="x-large" class="mb-3 text-medium-emphasis" />
      <div class="text-h6 mb-1">No extensions match the current filters</div>
      <div class="text-body-2 text-medium-emphasis mb-4">
        The catalogue is not empty — the search text and the type, maturity and hardware filters
        exclude every extension in it.
      </div>
      <v-btn color="primary" variant="tonal" @click="$emit('clearFilters')">Reset filters</v-btn>
    </template>

    <template v-else>
      <v-icon :icon="kaapanaIcons.info" size="x-large" class="mb-3 text-medium-emphasis" />
      <div class="text-h6 mb-1">No extensions available yet</div>
      <div class="text-body-2 text-medium-emphasis mb-4">
        <template v-if="props.canUpdateExtensions">
          Download the catalogue from the configured Helm repository to get started.
        </template>
        <template v-else>
          Nothing has been published to this platform's Helm repository yet. An administrator can
          download the catalogue.
        </template>
      </div>
      <v-btn
        v-if="props.canUpdateExtensions"
        color="primary"
        variant="flat"
        :prepend-icon="kaapanaIcons.refresh"
        :loading="props.busy"
        :disabled="props.busy"
        @click="$emit('updateExtensions')"
      >
        Download latest extensions
      </v-btn>
    </template>
  </div>
</template>

<style scoped>
.extensions-empty-state {
  max-width: 520px;
  margin-inline: auto;
}
</style>
