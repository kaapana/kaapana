<!--
  LogPageLayout.vue
  Consistent outer wrapper for all log source pages/panels.
  Provides the standard container padding and an optional header slot.
-->
<template>
  <v-container fluid>
    <v-container class="pad-lg">
      <slot />
    </v-container>
  </v-container>
</template>
