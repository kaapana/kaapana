<template>
  <v-container fluid class="text-left">
    <v-row justify="center">
      <v-col sm="12" md="6" xl="4">
        <WorkflowExecution @successful="onSuccessful" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { WorkflowExecution } from "@kaapana/base-ui/workflow-execution";
import "@kaapana/base-ui/workflow-execution.css";
import { navigateShell } from "@kaapana/base-ui";

// Hand off via the shell so it doesn't reload and can report an unavailable
// view; served standalone navigateShell falls back to a top-level navigation.
function onSuccessful() {
  navigateShell("/web/workflows/workflows");
}
</script>

<style lang="scss"></style>
