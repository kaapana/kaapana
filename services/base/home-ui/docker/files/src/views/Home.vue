<template>
  <v-container fluid>
    <div v-if="isAuthenticated">
      <v-row>
        <v-col cols="12">
          <BrandingHeader />
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12">
          <WorkflowIntro />
        </v-col>
      </v-row>
      <!-- Natural heights: the three cards' content lengths differ a lot, so
           the default stretch would pad the shorter two to the height of the
           notification list. -->
      <v-row align="start">
        <v-col cols="12" md="4">
          <UtilizationPanel />
        </v-col>
        <v-col cols="12" md="4">
          <ProjectStatsCard />
        </v-col>
        <v-col cols="12" md="4">
          <NotificationsCard />
        </v-col>
      </v-row>
    </div>
    <div v-else>
      <v-row align="center" justify="center" class="fill-height">
        <v-col cols="12">
          <v-card>
            <v-card-text class="text-left">
              <h1>Thank you for visiting us. We hope to see you again!</h1>
              <p>
                In order to log in again, please reload the page or
                <a @click="reloadPage()">click here</a>
                .
              </p>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>
  </v-container>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { notify } from '@kyvg/vue3-notification'
import BrandingHeader from '@/components/BrandingHeader.vue'
import WorkflowIntro from '@/components/WorkflowIntro.vue'
import UtilizationPanel from '@/components/UtilizationPanel.vue'
import ProjectStatsCard from '@/components/ProjectStatsCard.vue'
import NotificationsCard from '@/components/NotificationsCard.vue'
import { useAuthStore, useProjectStore } from '@kaapana/base-ui'

const authStore = useAuthStore()
const { isAuthenticated } = storeToRefs(authStore)

// Router guard resolved auth before this view mounts. Resolving the project
// redirects a document served without the /project/<short_id> prefix onto the
// user's first project.
if (isAuthenticated.value) {
  // Without a project the cards render unscoped or empty, so the failure has to
  // be visible; the rest of the page still works.
  useProjectStore()
    .getSelectedProject()
    .catch((err: any) => {
      notify({
        type: 'error',
        title: 'Failed to load projects',
        text: err?.response?.data?.detail ?? err?.message,
      })
    })
}

function reloadPage() {
  window.location.reload()
}
</script>
