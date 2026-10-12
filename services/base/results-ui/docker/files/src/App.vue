<script setup lang="ts">
import { useShellSettings } from '@kaapana/base-ui'

const { viewKey } = useShellSettings()
</script>

<template>
  <div id="app">
    <v-app>
      <notifications position="bottom right" width="20%" :duration="5000" />
      <v-main>
        <router-view :key="viewKey"></router-view>
      </v-main>
    </v-app>
  </div>
</template>
