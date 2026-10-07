<script setup lang="ts">
import { ErrorDetailsDialog, navigateShell, useShellSettings } from '@kaapana/base-ui'
import { useFailureDetailsStore, type FailureDetails } from '@/stores/failureDetails'

const { viewKey } = useShellSettings()
const failureDetails = useFailureDetailsStore()

// A failure notification carries its details in `data.failure`, a success may
// carry the view to open in `data.shellRoute` (see utils/notify.ts).
function onNotificationClick(item: { data?: unknown }) {
  const data = item.data as { failure?: FailureDetails; shellRoute?: string } | undefined
  if (data?.failure) failureDetails.show(data.failure)
  else if (data?.shellRoute) navigateShell(data.shellRoute)
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
        <router-view :key="viewKey" />
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
