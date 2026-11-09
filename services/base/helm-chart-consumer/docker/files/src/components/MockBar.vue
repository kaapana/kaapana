<template>
  <!-- Controls of the mock itself. Not part of the proposed UI, hence the inverted colour. -->
  <v-app-bar color="surface-variant" flat>
    <div class="d-flex align-center ga-2 px-4 mock-title">
      <v-icon icon="mdi-test-tube" />
      <span class="text-body-2 font-weight-medium">UI mock · Helm Chart Consumer</span>
    </div>
    <v-spacer />
    <div class="d-flex align-center ga-2 pr-2">
      <v-select
        :model-value="mock.personaId"
        :items="personas"
        item-title="name"
        item-value="id"
        label="Viewing as"
        density="compact"
        variant="outlined"
        hide-details
        class="persona-select"
        @update:model-value="mock.switchPersona($event)"
      >
        <template #item="{ props: itemProps, item }">
          <v-list-item v-bind="itemProps" :subtitle="item.raw.summary" />
        </template>
      </v-select>
      <StoryRef ids="5.1" />
      <v-checkbox
        v-model="mock.showStoryRefs"
        label="Story references"
        density="compact"
        hide-details
        class="mx-2 flex-grow-0"
      />
      <v-btn variant="text" prepend-icon="mdi-format-list-checks" @click="mock.storyPanel = true">
        User stories
      </v-btn>
      <v-menu location="bottom end">
        <template #activator="{ props: activator }">
          <v-btn
            v-bind="activator"
            :icon="kaapanaIcons.more"
            variant="text"
            aria-label="Mock menu"
          />
        </template>
        <v-list density="compact">
          <v-list-item
            :prepend-icon="kaapanaIcons.settings"
            title="Concept options…"
            @click="optionsOpen = true"
          />
          <v-list-item
            :prepend-icon="kaapanaIcons.restart"
            title="Simulate platform restart"
            subtitle="Story 12.1"
            :disabled="mock.restarting"
            @click="restart"
          />
          <v-list-item
            :prepend-icon="mock.dark ? 'mdi-weather-sunny' : 'mdi-weather-night'"
            :title="mock.dark ? 'Light mode' : 'Dark mode'"
            @click="mock.dark = !mock.dark"
          />
          <v-divider />
          <v-list-item
            :prepend-icon="kaapanaIcons.refresh"
            title="Reset mock data"
            @click="mock.reset()"
          />
        </v-list>
      </v-menu>
    </div>
  </v-app-bar>

  <v-dialog v-model="optionsOpen" max-width="600">
    <v-card :elevation="5">
      <v-card-title>Concept options</v-card-title>
      <v-card-text>
        <p class="text-body-2 text-medium-emphasis mb-4">
          Open questions of the concept change how the mock behaves. Pick an answer to try it out.
        </p>
        <v-radio-group v-model="mock.options.volumesOnUndeploy" color="primary">
          <template #label>
            <span class="text-subtitle-2">Q5 · Workspace volumes on undeploy</span>
          </template>
          <v-radio value="ask" label="The principal investigator decides in the undeploy dialog" />
          <v-radio value="delete" label="Always delete them with the application" />
          <v-radio value="keep" label="Always keep them" />
        </v-radio-group>
        <v-radio-group v-model="mock.options.newAppDefault" color="primary">
          <template #label>
            <span class="text-subtitle-2">Q8 · Newly registered applications</span>
          </template>
          <v-radio value="disabled" label="Disabled in all projects until an admin enables them" />
          <v-radio value="enabled" label="Enabled in all projects" />
        </v-radio-group>
        <v-radio-group v-model="mock.options.projectDeletion" color="primary" hide-details>
          <template #label>
            <span class="text-subtitle-2">Q9 · Deleting a project with deployed applications</span>
          </template>
          <v-radio value="undeploy" label="Undeploy the applications together with the project" />
          <v-radio value="refuse" label="Refuse until all applications are undeployed" />
        </v-radio-group>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="optionsOpen = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { kaapanaIcons } from '@kaapana/base-ui'
import { personas } from '@/mock/data'
import { useMockStore } from '@/stores/mock'
import StoryRef from './StoryRef.vue'

const mock = useMockStore()
const router = useRouter()
const optionsOpen = ref(false)

function restart() {
  router.push('/applications')
  mock.simulateRestart()
}
</script>

<style scoped>
.persona-select {
  width: 220px;
  flex: none;
}
@media (max-width: 1100px) {
  .mock-title {
    display: none !important;
  }
}
</style>
