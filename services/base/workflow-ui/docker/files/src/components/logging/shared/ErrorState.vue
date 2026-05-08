<template>
  <v-row class="d-flex justify-center">
    <v-col cols="12">
      <v-alert type="error" prominent>
        <slot>{{ message }}</slot>
      </v-alert>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
defineProps<{ message?: string }>()
</script>
