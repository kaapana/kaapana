<!--
  LogsOverview.vue
  Combined log hub – renders each log source panel in its own tab.
  Each panel owns its own state and search logic independently.
-->
<template>
  <v-container fluid>
    <v-container class="pad-lg">

      <v-row class="mb-4">
        <v-col cols="12">
          <h1 class="text-h5 mb-4">Logs</h1>
          <v-tabs v-model="activeTab" color="primary">
            <v-tab value="workflow" prepend-icon="mdi-sitemap">Workflow Logs</v-tab>
            <v-tab value="loki"     prepend-icon="mdi-text-search">Loki (advanced)</v-tab>
          </v-tabs>
        </v-col>
      </v-row>

      <v-tabs-window v-model="activeTab">
        <!--
          v-tabs-window-item uses eager rendering so each panel keeps its state
          even when the tab is not active.
        -->
        <v-tabs-window-item value="workflow" eager>
          <WorkflowLogsPanel />
        </v-tabs-window-item>

        <v-tabs-window-item value="loki" eager>
          <LokiLogsPanel />
        </v-tabs-window-item>
      </v-tabs-window>

    </v-container>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import WorkflowLogsPanel from '@/components/logging/workflow/WorkflowLogsPanel.vue'
import LokiLogsPanel from '@/components/logging/loki/LokiLogsPanel.vue'

const activeTab = ref('workflow')
</script>
