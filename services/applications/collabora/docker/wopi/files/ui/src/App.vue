<template>
  <v-app>
    <v-main>
      <DocumentList :key="viewKey" />
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { useShellSettings } from '@kaapana/base-ui'
import DocumentList from '@/components/DocumentList.vue'

const { viewKey } = useShellSettings()
</script>
