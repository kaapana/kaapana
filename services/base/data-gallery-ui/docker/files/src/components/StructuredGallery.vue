<template>
  <div>
    <div v-for="(studies, patient) in patients" :key="patient">
      <v-lazy
        :options="{
          threshold: 0.3,
        }"
        transition="fade-transition"
        class="fill-height"
        :min-height="100"
      >
        <PatientView :studies="studies" />
      </v-lazy>
    </div>
  </div>
</template>

<script setup lang="ts">
import PatientView from './PatientView.vue'
import type { Patients } from '@/types'

withDefaults(defineProps<{ patients?: Patients }>(), {
  patients: () => ({}),
})
</script>

<style></style>
