<template>
  <v-app>
    <notifications position="bottom right" width="20%" :duration="5000" />
    <v-main>
      <router-view :key="viewKey"></router-view>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { useShellSettings } from '@kaapana/base-ui'

const { viewKey } = useShellSettings()
</script>

<style lang="scss">
/* No font-family, font-size or text colour is set here on purpose: the platform
   typeface and the theme's foreground roles come from createKaapanaVuetify, and
   a local override here would apply the wrong type scale and a fixed grey that
   ignores the dark theme (design guidelines, "Typography" and "Color"). */
@media (min-width: 2100px) {
  .container--fluid {
    max-width: 2100px !important;
  }
}
</style>
