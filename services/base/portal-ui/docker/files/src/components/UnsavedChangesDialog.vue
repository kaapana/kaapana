<script setup lang="ts">
import { useViewStateStore } from '@/stores/viewState'

// Shell-level confirm behind viewState.confirmLeave(): one dialog for every
// state-destroying action (project switch, menu navigation, corner refresh).
const viewState = useViewStateStore()
</script>

<template>
  <v-dialog
    :model-value="viewState.confirmVisible"
    width="440"
    @update:model-value="(open: boolean) => open || viewState.resolveLeave(false)"
  >
    <v-card>
      <v-card-title>Unsaved changes</v-card-title>
      <v-card-text>
        Leaving this view reloads it. Any unsaved changes (such as filters or
        form input) will be lost.
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="viewState.resolveLeave(false)">Stay</v-btn>
        <v-btn color="primary" @click="viewState.resolveLeave(true)">Leave view</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
