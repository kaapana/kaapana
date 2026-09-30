<script setup lang="ts">
import { kaapanaIcons } from '@/utils/extensionIcons'

// Empty state of the catalogue table. Tells "nothing exists", "the filters
// exclude everything" and "the list could not be loaded" apart, each with its
// own action.
const props = defineProps<{
  state: 'error' | 'no-matches' | 'empty'
  /** Whether the failed load carried detail worth a disclosure. */
  hasErrorDetails?: boolean
  /** Whether the current user may trigger a catalogue download. */
  canUpdateExtensions?: boolean
  /** A catalogue download is already running. */
  busy?: boolean
  /** A reload triggered from here is already running. */
  retrying?: boolean
}>()

defineEmits<{
  (event: 'retry'): void
  (event: 'showDetails'): void
  (event: 'clearFilters'): void
  (event: 'updateExtensions'): void
}>()
</script>

<template>
  <div data-testid="extensions-empty-state">
    <v-empty-state
      v-if="props.state === 'error'"
      :icon="kaapanaIcons.error"
      color="error"
      size="56"
      title="Could not load the extension list"
      text="The extension service could not be reached or reported an error. Try again, or contact your administrator if it persists."
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
      title="No extensions match the current filters"
      text="The catalogue is not empty — the search text and the type, maturity and hardware filters exclude every extension in it."
    >
      <template #actions>
        <v-btn color="primary" variant="text" @click="$emit('clearFilters')">Reset filters</v-btn>
      </template>
    </v-empty-state>

    <v-empty-state
      v-else
      size="56"
      title="No extensions available yet"
      :text="
        props.canUpdateExtensions
          ? 'Download the extension catalogue from the configured container registry to get started.'
          : 'No extension catalogue has been downloaded to this platform yet. An administrator can download it.'
      "
    >
      <template v-if="props.canUpdateExtensions" #actions>
        <v-btn
          color="primary"
          variant="text"
          :prepend-icon="kaapanaIcons.refresh"
          :loading="props.busy"
          :disabled="props.busy"
          @click="$emit('updateExtensions')"
        >
          Download latest extensions
        </v-btn>
      </template>
    </v-empty-state>
  </div>
</template>
