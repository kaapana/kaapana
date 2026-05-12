<!-- Just for development purposes -->
<script setup lang="ts">
import { useTheme } from 'vuetify'

const theme = useTheme()

function toggleTheme() {
  theme.global.name.value =
    theme.global.name.value === 'kaapanaThemeDark'
      ? 'kaapanaThemeLight'
      : 'kaapanaThemeDark'
}
</script>

<template>
  <v-btn @click="toggleTheme">
    T
  </v-btn>
</template>