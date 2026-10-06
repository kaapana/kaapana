<script setup lang="ts">
import { ErrorDetailsDialog, useShellSettings } from '@kaapana/base-ui'
import { useFailureDetailsStore, type FailureDetails } from '@/stores/failureDetails'

const { viewKey } = useShellSettings()
const failureDetails = useFailureDetailsStore()

function onNotificationClick(item: { data?: unknown }) {
  const failure = (item.data as { failure?: FailureDetails } | undefined)?.failure
  if (failure) failureDetails.show(failure)
}
</script>

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
      <router-view :key="viewKey" />
    </v-main>
    <ErrorDetailsDialog
      v-model="failureDetails.open"
      :title="failureDetails.current?.title"
      :text="failureDetails.current?.text"
      :error="failureDetails.current?.error ?? null"
    />
  </v-app>
</template>
