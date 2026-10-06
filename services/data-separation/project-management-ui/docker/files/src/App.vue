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
      <v-container v-if="bootError" fluid class="pm-view">
        <FailureAlert
          title="User not loaded"
          text="Could not load your user account."
          :error="bootError"
          :retry="loadCurrentUser"
        />
      </v-container>
      <router-view v-else :key="viewKey" />
    </v-main>
    <ErrorDetailsDialog
      v-model="failureDetails.open"
      :title="failureDetails.current?.title"
      :text="failureDetails.current?.text"
      :error="failureDetails.current?.error ?? null"
    />
  </v-app>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import { ErrorDetailsDialog, useShellSettings } from '@kaapana/base-ui'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import store from '@/common/store'
import { UserItem } from '@/common/types'
import { aiiApiGet } from '@/common/services'
import { usePermissionsStore } from '@/permissions/permissions.store'
import { usePolicyStore } from '@/stores/policy'
import { notifyFailure } from '@/utils/notifyFailure'
import FailureAlert from '@/components/FailureAlert.vue'

const { viewKey } = useShellSettings()
const failureDetails = useFailureDetailsStore()

// A failure notification carries its details in `data.failure` (see
// utils/notifyFailure.ts); selecting it opens ErrorDetailsDialog.
function onNotificationClick(item: { data?: unknown }) {
  const failure = (item.data as { failure?: unknown } | undefined)?.failure
  if (failure) failureDetails.show(failure as never)
}
const permissions = usePermissionsStore()
const policy = usePolicyStore()
const bootError = ref<unknown>(null)

onMounted(() => {
  policy.getPolicyData()
  loadCurrentUser()
})

async function loadCurrentUser() {
  bootError.value = null
  let currentUser: UserItem
  try {
    currentUser = await aiiApiGet('users/current')
  } catch (error) {
    bootError.value = error
    return
  }
  store.updateUser(currentUser)
  try {
    await permissions.loadUserRights(currentUser.id)
  } catch (error) {
    notifyFailure(
      'Project rights not loaded',
      'Could not load your project rights; controls they grant stay hidden.',
      error,
    )
  }
}
</script>

<style>
/* A readable maximum for the project tables; the container centres itself in
   the space beyond it. */
.pm-view {
  max-width: 1600px;
}

.pm-search {
  max-width: 420px;
}

.pm-pending {
  background-color: rgba(var(--v-theme-warning), 0.12);
}
</style>
