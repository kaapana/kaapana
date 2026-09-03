<script setup lang="ts">
import { useShellSettings } from '@kaapana/base-ui'

const { viewKey } = useShellSettings()
</script>

<template>
  <div id="app">
    <v-app>
      <!-- Transient notifications: action outcomes, bottom-right per the
           guidelines' "Notifications and alerts". -->
      <notifications position="bottom right" width="20%" :duration="5000" />
      <v-main>
        <router-view :key="viewKey"></router-view>
      </v-main>
    </v-app>
  </div>
</template>

<style lang="scss">
// No font-family, font-size or colour is set here on purpose. The platform
// typeface and the light/dark text colours come from the shared theme via
// createKaapanaVuetify(); overriding them locally is what made this view
// render in Helvetica on a hardcoded #333 in both themes.
@media (min-width: 2100px) {
  .container--fluid {
    max-width: 2100px !important;
  }
}
</style>
