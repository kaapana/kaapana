<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  description?: string | null
}>()

const trimmed = computed(() => props.description?.trim() ?? '')
</script>

<template>
  <section v-if="trimmed">
    <div class="section-title">Description</div>
    <div class="text-body-2">{{ trimmed }}</div>
  </section>
</template>

<style scoped>
.section-title {
  font-weight: 500;
  margin-bottom: 8px;
}
</style>
