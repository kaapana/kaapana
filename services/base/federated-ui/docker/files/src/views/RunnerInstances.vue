<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center flex-wrap">
            <p class="mx-4 my-2">Instance Overview</p>
            <add-remote-instance class="mx-4" @refreshRemoteFromAdding="getKaapanaInstances()"></add-remote-instance>
            <v-btn class="mx-4" @click="checkForRemoteUpdates" color="primary" size="small" variant="outlined" rounded>
              sync remotes
            </v-btn>
          </v-card-title>
          <v-card-text>
            <v-container fluid>
              <v-row dense>
                <v-col v-for="instance in remoteInstances" :key="instance.id" cols="6" align="left">
                  <KaapanaInstance :instance="instance" @refreshView="getKaapanaInstances()"></KaapanaInstance>
                </v-col>
              </v-row>
            </v-container>
          </v-card-text>
          <v-card-actions></v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import { kaapanaApiService } from '@kaapana/base-ui'

import AddRemoteInstance from '@/components/AddRemoteInstance.vue'
import KaapanaInstance from '@/components/KaapanaInstance.vue'

const polling = ref(0)
const remoteInstances = ref<Record<string, any>>({})

function getKaapanaInstances() {
  kaapanaApiService
    .federatedClientApiPost('/get-kaapana-instances')
    .then((response: any) => {
      remoteInstances.value = response.data
    })
    .catch((err: any) => {
      console.log(err)
      notify({
        type: 'error',
        title: 'Failed to load instances',
      })
    })
}

function checkForRemoteUpdates() {
  kaapanaApiService
    .syncRemoteInstances()
    .then(() => {
      getKaapanaInstances()
    })
    .catch((err: any) => {
      console.log(err)
      notify({
        type: 'error',
        title: 'Failed to sync remote instances',
        text: err?.response?.data?.detail ?? err.message,
      })
    })
}

function clearExtensionsInterval() {
  window.clearInterval(polling.value)
}

function startExtensionsInterval() {
  polling.value = window.setInterval(() => {
    getKaapanaInstances()
  }, 15000)
}

onMounted(() => {
  getKaapanaInstances()
  startExtensionsInterval()
})

onBeforeUnmount(() => {
  clearExtensionsInterval()
})
</script>

<style lang="scss"></style>
