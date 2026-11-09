<template>
  <v-navigation-drawer v-model="mock.storyPanel" location="right" temporary width="440">
    <div class="pa-4">
      <div class="d-flex align-center mb-2">
        <h2 class="text-h6">User stories in this mock</h2>
        <v-spacer />
        <v-btn
          :icon="kaapanaIcons.close"
          variant="text"
          size="small"
          aria-label="Close user stories"
          @click="mock.storyPanel = false"
        />
      </div>
      <p class="text-body-2 text-medium-emphasis mb-4">
        {{ mvpCount }} of the 24 MVP stories, and the Release 2 stories
        {{ release2.join(', ') }} where an answer in QandA.md needs them. "Show me" switches to a
        fitting person, opens the view and marks where the story is covered.
      </p>

      <template v-for="group in groups" :key="group.epic">
        <div class="text-overline mt-2">{{ group.epic }}</div>
        <v-sheet
          v-for="story in group.stories"
          :key="story.id"
          border
          rounded="lg"
          class="pa-3 mb-2"
        >
          <div class="d-flex align-start ga-2">
            <v-chip size="x-small" label color="secondary" variant="flat" class="mt-1">{{
              story.id
            }}</v-chip>
            <div class="flex-grow-1">
              <div class="text-subtitle-2">
                {{ story.title }}
                <v-chip v-if="story.priority !== 'MVP'" size="x-small" variant="tonal" class="ml-1">
                  {{ story.priority }}
                </v-chip>
              </div>
              <div class="text-body-2 text-medium-emphasis">{{ story.statement }}</div>
              <div class="text-caption mt-1">{{ story.where }}</div>
            </div>
          </div>
          <div class="d-flex justify-end">
            <v-btn color="primary" variant="text" size="small" @click="showMe(story)"
              >Show me</v-btn
            >
          </div>
        </v-sheet>
      </template>

      <div class="text-overline mt-4">Not part of this mock</div>
      <v-list density="compact" class="py-0">
        <v-list-item
          v-for="s in excludedStories"
          :key="s.id"
          :title="`${s.id} ${s.title}`"
          :subtitle="s.reason"
        />
      </v-list>
      <p class="text-caption text-medium-emphasis mt-2">
        With Story references on, chips such as Q5 mark where the mock shows an answer from
        QandA.md, or a question that is not decided yet.
      </p>
    </div>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { kaapanaIcons } from '@kaapana/base-ui'
import { coveredStories, excludedStories, type StoryLink } from '@/mock/stories'
import { useMockStore } from '@/stores/mock'

const mock = useMockStore()
const router = useRouter()

const mvpCount = coveredStories.filter((s) => s.priority === 'MVP').length
const release2 = coveredStories.filter((s) => s.priority === 'Release 2').map((s) => s.id)

const groups = computed(() => {
  const out: { epic: string; stories: StoryLink[] }[] = []
  for (const story of coveredStories) {
    const last = out[out.length - 1]
    if (last && last.epic === story.epic) last.stories.push(story)
    else out.push({ epic: story.epic, stories: [story] })
  }
  return out
})

async function showMe(story: StoryLink) {
  mock.storyPanel = false
  if (mock.dirty) {
    // The shell asks before the unsaved deploy form is left.
    router.push(story.route)
    return
  }
  mock.applyPersona(story.persona)
  const project = story.project ?? 'lung-ct'
  if (mock.accessibleProjects.some((p) => p.id === project)) mock.projectId = project
  mock.showStoryRefs = true
  await router.push(story.route)
  await nextTick()
  // Let the view render its data before looking for the marker.
  setTimeout(() => {
    mock.highlightStory = story.id
    const anchor = document.querySelector(`[data-story-ref~="${story.id}"]`)
    anchor?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    setTimeout(() => {
      if (mock.highlightStory === story.id) mock.highlightStory = null
    }, 2600)
  }, 300)
}
</script>
