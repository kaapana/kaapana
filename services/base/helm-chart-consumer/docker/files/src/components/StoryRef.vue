<template>
  <!-- The anchor stays in the DOM while the chips are hidden, so "Show me" can find it. -->
  <span class="story-ref" :data-story-ref="list.join(' ')">
    <template v-if="mock.showStoryRefs">
      <v-tooltip v-for="id in list" :key="id" location="top" :text="tooltip(id)">
        <template #activator="{ props: activator }">
          <v-chip
            v-bind="activator"
            size="x-small"
            label
            color="secondary"
            variant="flat"
            class="ml-1"
            :class="{ 'story-ref--flash': mock.highlightStory === id }"
            :aria-label="tooltip(id)"
          >
            {{ id }}
          </v-chip>
        </template>
      </v-tooltip>
    </template>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useMockStore } from '@/stores/mock'
import { storyTitles } from '@/mock/stories'

const props = defineProps<{ ids: string }>()
const mock = useMockStore()

const list = computed(() => props.ids.split(/[\s,]+/).filter(Boolean))

function tooltip(id: string) {
  const title = storyTitles[id]
  return id.startsWith('Q') ? (title ?? id) : `Story ${id}${title ? ` · ${title}` : ''}`
}
</script>
