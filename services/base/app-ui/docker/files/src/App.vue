<script setup lang="ts">
import { useShellSettings } from '@kaapana/base-ui'

const { viewKey } = useShellSettings()
</script>

<template>
  <v-app>
    <notifications position="bottom right" width="20%" :duration="5000" />
    <v-main>
      <router-view :key="viewKey" />
    </v-main>
  </v-app>
</template>

<style lang="scss">
#app {
  font-family: "Avenir", Helvetica, Arial, sans-serif;
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: 14px;
  line-height: 1.42857143;
  color: #333;
}

@media (min-width: 2100px) {
  .v-container--fluid {
    max-width: 2100px !important;
  }
}
</style>
