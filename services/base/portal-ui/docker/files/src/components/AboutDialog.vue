<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiErrorInfo, kaapanaIcons, type ApiErrorInfo } from '@kaapana/base-ui'
import { useFailureDetailsStore } from '@/stores/failureDetails'
import http from '@/api/http'

interface CommonData {
  version?: string
}

const failureDetails = useFailureDetailsStore()

const dialog = ref(false)
const versionError = ref<ApiErrorInfo | null>(null)
const VERSION_ERROR_TEXT = 'The version information could not be loaded.'
const versionObj = ref<Record<string, string>>({
  'Repository URL': 'https://codebase.helmholtz.cloud/kaapana/kaapana',
})

// "Version-Info | Build-Timestamp: ... | Build-Branch: ..." → key/value rows
function formatVersions(versionText?: string) {
  if (!versionText) return
  versionText.split('|').forEach((versionItem) => {
    const cleaned = versionItem.trim()
    const keyEndPos = cleaned.indexOf(':')
    versionObj.value[cleaned.substring(0, keyEndPos)] = cleaned.substring(keyEndPos + 1).trim()
  })
}

const loadingVersions = ref(false)

async function loadVersions() {
  versionError.value = null
  loadingVersions.value = true
  try {
    // Served by portal-ui nginx from the portal-ui-config ConfigMap mount.
    const res = await http.get<CommonData>('/jsons/commonData.json')
    formatVersions(res.data.version)
  } catch (error) {
    versionError.value = apiErrorInfo(error)
    console.error('Could not load commonData.json', error)
  } finally {
    loadingVersions.value = false
  }
}

onMounted(loadVersions)
</script>

<template>
  <v-dialog v-model="dialog" max-width="600">
    <template #activator="{ props }">
      <v-btn v-bind="props" icon variant="text" size="small" title="About Platform">
        <v-icon :icon="kaapanaIcons.info"></v-icon>
      </v-btn>
    </template>

    <v-card>
      <v-container fluid>
        <v-card-title class="d-flex align-center ga-3 text-h5">
          <img src="/assets/img/logo.webp" alt="Kaapana" height="36" />
          Kaapana
        </v-card-title>
        <v-card-text class="pt-2 pb-8">
          <v-alert type="warning" variant="tonal" density="compact" class="mb-4">
            Kaapana is not a medical device. It is intended for research purposes only and must not
            be used for clinical diagnosis or treatment decisions.
          </v-alert>
          <div class="text-h6">Links</div>
          <div class="py-2 d-flex flex-wrap ga-2">
            <v-btn color="primary" variant="tonal" target="_blank" href="https://kaapana.ai">
              Website
              <v-icon end>mdi-web</v-icon>
            </v-btn>
            <v-btn
              color="primary"
              variant="tonal"
              target="_blank"
              href="https://join.slack.com/t/kaapana/shared_invite/zt-hilvek0w-ucabihas~jn9PDAM0O3gVQ/"
            >
              Join Slack
              <v-icon end>mdi-slack</v-icon>
            </v-btn>
            <v-btn
              color="primary"
              variant="tonal"
              target="_blank"
              href="https://codebase.helmholtz.cloud/kaapana/kaapana/-/issues"
            >
              Report Issue
              <v-icon end :icon="kaapanaIcons.externalLink"></v-icon>
            </v-btn>
          </div>
          <div class="text-h6 py-4">Version Information</div>
          <v-alert
            v-if="versionError"
            type="error"
            variant="tonal"
            density="compact"
            class="mb-2"
            :text="VERSION_ERROR_TEXT"
          >
            <template #append>
              <v-btn
                variant="text"
                size="small"
                @click="
                  failureDetails.show({
                    title: 'Version information',
                    text: VERSION_ERROR_TEXT,
                    error: versionError!,
                  })
                "
              >
                Details
              </v-btn>
              <v-btn variant="text" size="small" :loading="loadingVersions" @click="loadVersions">
                Try again
              </v-btn>
            </template>
          </v-alert>
          <v-row v-for="(value, key) in versionObj" :key="key">
            <v-col cols="3" class="py-2">
              <span class="font-weight-medium">{{ key }}:</span>
            </v-col>
            <v-col class="py-2">
              <a v-if="value.startsWith('http')" :href="value" target="_blank">{{ value }}</a>
              <template v-else>{{ value }}</template>
            </v-col>
          </v-row>
        </v-card-text>

        <v-card-actions class="justify-center">
          <v-btn color="primary" variant="text" @click="dialog = false">Close</v-btn>
        </v-card-actions>
      </v-container>
    </v-card>
  </v-dialog>
</template>
