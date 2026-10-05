<script setup lang="ts" generic="T">
const props = defineProps<{
  items: T[]
  loading: boolean
  itemKey: (item: T) => string
  cardLabel?: (item: T) => string
}>()

const emit = defineEmits<{
  (event: 'select', item: T): void
}>()

function cardBindings(item: T) {
  if (!props.cardLabel) return {}
  return { role: 'button', tabindex: 0, 'aria-label': props.cardLabel(item) }
}

function cardListeners(item: T) {
  if (!props.cardLabel) return {}
  return {
    click: () => emit('select', item),
    keydown: (event: KeyboardEvent) => {
      if (event.key !== 'Enter' && event.key !== ' ') return
      event.preventDefault()
      emit('select', item)
    },
  }
}
</script>

<template>
  <v-row v-if="props.loading && props.items.length === 0" data-testid="cards-loading">
    <v-col v-for="index in 3" :key="index" cols="12" md="6" lg="4">
      <v-skeleton-loader type="article" />
    </v-col>
  </v-row>

  <slot v-else-if="props.items.length === 0" name="empty" />

  <v-row v-else>
    <v-col v-for="item in props.items" :key="props.itemKey(item)" cols="12" md="6" lg="4">
      <v-card
        class="h-100 d-flex flex-column"
        data-testid="card"
        v-bind="cardBindings(item)"
        v-on="cardListeners(item)"
      >
        <slot name="card" :item="item" />
      </v-card>
    </v-col>
  </v-row>
</template>
