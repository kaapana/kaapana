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
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { kaapanaIcons } from '@kaapana/base-ui'
import { personas } from '@/mock/data'
import { useMockStore } from '@/stores/mock'
import StoryRef from './StoryRef.vue'

const mock = useMockStore()
const router = useRouter()

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
