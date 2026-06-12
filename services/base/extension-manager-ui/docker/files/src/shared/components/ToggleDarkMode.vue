<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from 'vuetify'

const DARK_THEME = 'kaapanaThemeDark'
const LIGHT_THEME = 'kaapanaThemeLight'

const theme = useTheme()

const isDark = computed(() => theme.global.name.value === DARK_THEME)

function toggleTheme() {
  theme.global.name.value = isDark.value ? LIGHT_THEME : DARK_THEME
}
</script>

<template>
  <v-btn
    :icon="isDark ? 'mdi-weather-sunny' : 'mdi-weather-night'"
    variant="text"
    :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
    @click="toggleTheme"
  />
</template>
