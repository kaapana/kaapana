<script setup lang="ts">
import { ErrorDetailsDialog, useShellSettings } from '@kaapana/base-ui'
import { useFailureDetailsStore } from '@/stores/failureDetails'

const { viewKey } = useShellSettings()
const failureDetails = useFailureDetailsStore()

// A failure notification carries its details in `data.failure` (see
// utils/notifyFailure.ts); selecting it opens ErrorDetailsDialog.
function onNotificationClick(item: { data?: unknown }) {
  const failure = (item.data as { failure?: unknown } | undefined)?.failure
  if (failure) failureDetails.show(failure as never)
}
</script>

<template>
  <div id="app">
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
  </div>
</template>
