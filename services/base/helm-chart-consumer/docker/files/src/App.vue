<template>
  <v-app>
    <notifications position="bottom right" width="20%" :duration="5000" close-on-click />
    <MockBar />
    <ShellNav />
    <StoryPanel />
    <v-main>
      <!-- The shell reloads a view when the project changes; switching the person does the same here. -->
      <router-view :key="`${mock.projectId}:${mock.personaId}`" />
    </v-main>
    <ShellUnsavedDialog />
    <AppWindow />
  </v-app>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useTheme } from 'vuetify'
import { KAAPANA_THEME_DARK, KAAPANA_THEME_LIGHT } from '@kaapana/base-ui'
import AppWindow from '@/components/AppWindow.vue'
import MockBar from '@/components/MockBar.vue'
import ShellNav from '@/components/ShellNav.vue'
import ShellUnsavedDialog from '@/components/ShellUnsavedDialog.vue'
import StoryPanel from '@/components/StoryPanel.vue'
import { useMockStore } from '@/stores/mock'

const mock = useMockStore()
const theme = useTheme()

watch(
  () => mock.dark,
  (dark) => {
    theme.global.name.value = dark ? KAAPANA_THEME_DARK : KAAPANA_THEME_LIGHT
  },
)
</script>

<style>
.story-ref .v-chip {
  vertical-align: middle;
}
.story-ref--flash {
  animation: story-flash 0.8s ease-in-out 3;
}
@keyframes story-flash {
  50% {
    box-shadow: 0 0 0 6px rgba(var(--v-theme-warning), 0.6);
  }
}
@media (prefers-reduced-motion: reduce) {
  .story-ref--flash {
    animation: none;
    outline: 3px solid rgb(var(--v-theme-warning));
  }
}
</style>
