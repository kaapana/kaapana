<script setup lang="ts">
import { ConfirmDialog } from '@kaapana/base-ui'
import { useViewStateStore } from '@/stores/viewState'

// Shell-level confirm behind viewState.confirmLeave(): one dialog for every
// state-destroying action (project switch, menu navigation, corner refresh).
// Escape, the backdrop and a stray Enter all mean "Stay".
const viewState = useViewStateStore()
</script>

<template>
  <!-- Leaving discards the view's work, so it is confirmed as destructive. -->
  <ConfirmDialog
    :model-value="viewState.confirmVisible"
    color="error"
    title="Unsaved changes"
    text="Leaving this view reloads it. Any unsaved changes (such as filters or form input) will be lost."
    cancel-text="Stay"
    confirm-text="Leave view"
    @confirm="viewState.resolveLeave(true)"
    @cancel="viewState.resolveLeave(false)"
  />
</template>
