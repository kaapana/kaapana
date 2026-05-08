<template>
  <LogPageLayout>
    <LokiLogsPanel />
  </LogPageLayout>
</template>

<script setup lang="ts">
import LogPageLayout from '@/components/logging/shared/LogPageLayout.vue'
import LokiLogsPanel from '@/components/logging/loki/LokiLogsPanel.vue'
</script>
