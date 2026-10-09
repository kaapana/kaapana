<template>
  <v-app>
    <v-main>
      <Documents :key="viewKey" />
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { useShellSettings } from '@kaapana/base-ui'
import Documents from '@/components/Documents.vue'

const { viewKey } = useShellSettings()
</script>
