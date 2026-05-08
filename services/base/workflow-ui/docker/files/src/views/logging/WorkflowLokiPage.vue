<template>
  <LogPageLayout>
    <WorkflowLokiPanel />
  </LogPageLayout>
</template>

<script setup lang="ts">
import LogPageLayout from '@/components/logging/shared/LogPageLayout.vue'
import WorkflowLokiPanel from '@/components/logging/loki/WorkflowLokiPanel.vue'
</script>
