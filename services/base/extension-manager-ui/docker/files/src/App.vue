<script setup lang="ts">
import { ErrorDetailsDialog, useShellSettings } from '@kaapana/base-ui'
import { useFailureDetailsStore, type FailureDetails } from '@/shared/stores/failureDetails'

const { viewKey } = useShellSettings()
const failureDetails = useFailureDetailsStore()

const tabs = [
  { title: 'Catalog', to: '/catalog' },
  { title: 'Extensions', to: '/extensions' },
  { title: 'Repositories', to: '/repositories' },
]

function onNotificationClick(item: { data?: unknown }) {
  const failure = (item.data as { failure?: FailureDetails } | undefined)?.failure
  if (failure) failureDetails.show(failure)
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
        <v-container class="extension-manager">
          <h1 class="text-h4 mb-2">Extension Manager</h1>
          <v-tabs color="primary" class="mb-6" aria-label="Extension Manager sections">
            <v-tab v-for="tab in tabs" :key="tab.to" :to="tab.to">{{ tab.title }}</v-tab>
          </v-tabs>
          <router-view :key="viewKey" />
        </v-container>
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

<style scoped>
.extension-manager {
  max-width: 1600px;
}
</style>
