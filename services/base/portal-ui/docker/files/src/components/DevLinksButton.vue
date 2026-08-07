<script setup lang="ts">
import type { DevLink } from '@/types/menu'

// Never rendered with an empty list — NavDrawer omits the slot instead, so with
// dev mode off the list item keeps its untouched markup.
defineProps<{ links: DevLink[] }>()
</script>

<template>
  <!-- Both buttons sit inside the drawer entry, which is itself a link. .stop
       keeps the click off it; the menu activator instead needs .prevent, since
       its own handler already stops propagation yet vue-router still routes. -->
  <v-btn
    v-if="links.length === 1"
    :href="links[0]!.path"
    target="_blank"
    rel="noopener"
    icon="mdi-api"
    variant="text"
    size="x-small"
    :title="links[0]!.label"
    @click.stop
  ></v-btn>
  <v-menu v-else>
    <template #activator="{ props }">
      <v-btn
        v-bind="props"
        icon="mdi-api"
        variant="text"
        size="x-small"
        title="API docs"
        @click.prevent
      ></v-btn>
    </template>
    <v-list density="compact">
      <v-list-item
        v-for="link in links"
        :key="link.path"
        :href="link.path"
        target="_blank"
        rel="noopener"
        :title="link.label"
      ></v-list-item>
    </v-list>
  </v-menu>
</template>
