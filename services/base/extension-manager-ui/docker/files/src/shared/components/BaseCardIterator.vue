<script setup lang="ts" generic="T">
const props = defineProps<{
  items: T[]
  loading: boolean
  error?: string | null
  emptyMessage: string
  itemKey: (item: T) => string
  minHeight?: string
}>()

const emit = defineEmits<{
  (event: 'select', item: T): void
}>()
</script>

<template>
  <v-alert v-if="props.error" type="error" class="mb-4">
    {{ props.error }}
  </v-alert>

  <v-row
    v-else-if="props.loading"
    class="d-flex justify-center align-center"
    :style="{ minHeight: props.minHeight ?? '240px' }"
  >
    <v-progress-circular indeterminate color="primary" size="64" />
  </v-row>

  <v-alert v-else-if="props.items.length === 0" type="info" class="mb-4">
    {{ props.emptyMessage }}
  </v-alert>

  <v-row v-else>
    <v-col v-for="item in props.items" :key="props.itemKey(item)" cols="12" md="6" lg="4">
      <v-card
        class="h-100"
        role="button"
        tabindex="0"
        @click="emit('select', item)"
        @keydown.enter.prevent="emit('select', item)"
        @keydown.space.prevent="emit('select', item)"
      >
        <slot name="cardBody" :item="item" />
      </v-card>
    </v-col>
  </v-row>
</template>
