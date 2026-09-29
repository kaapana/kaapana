<template>
  <v-app>
    <notifications
      position="bottom right"
      width="20%"
      :duration="5000"
      close-on-click
      @click="onNotificationClick"
    />
    <v-main>
      <router-view :key="viewKey"></router-view>
    </v-main>
    <ErrorDetailsDialog
      v-model="failureDetails.open"
      :title="failureDetails.current?.title"
      :text="failureDetails.current?.text"
      :error="failureDetails.current?.error ?? null"
    />
  </v-app>
</template>

<script setup lang="ts">
import { ErrorDetailsDialog, useShellSettings } from '@kaapana/base-ui'
import { useFailureDetailsStore } from '@/stores/failureDetails'

const { viewKey } = useShellSettings()
const failureDetails = useFailureDetailsStore()

// utils/notifyFailure.ts puts a failure's details in `data.failure`.
function onNotificationClick(item: { data?: unknown }) {
  const failure = (item.data as { failure?: unknown } | undefined)?.failure
  if (failure) failureDetails.show(failure as never)
}
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
