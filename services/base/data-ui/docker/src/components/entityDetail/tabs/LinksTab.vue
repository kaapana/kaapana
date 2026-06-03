<script setup lang="ts">
import { computed, ref } from 'vue'
import type { DataEntity, EntityLink } from '@/types/domain'
import { useEntityStore } from '@/stores/entityStore'

const props = defineProps<{
  entity: DataEntity
  navigateToEntity: (id: string | null | undefined) => void
}>()

const store = useEntityStore()

const CONTAINS = 'contains'

const outgoingByType = computed(() => groupByType(props.entity.outgoing_links ?? []))
const incomingByType = computed(() => groupByType(props.entity.incoming_links ?? []))

function groupByType(links: EntityLink[]): Array<{ type: string; links: EntityLink[] }> {
  const buckets = new Map<string, EntityLink[]>()
  for (const link of links) {
    const bucket = buckets.get(link.link_type) ?? []
    bucket.push(link)
    buckets.set(link.link_type, bucket)
  }
  return Array.from(buckets.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([type, items]) => ({ type, links: items }))
}

const addingChild = ref(false)
const addChildTargetId = ref('')
const addBusy = ref(false)
const localError = ref<string | null>(null)
const removingLinkId = ref<string | null>(null)

function openAddChild() {
  addingChild.value = true
  addChildTargetId.value = ''
  localError.value = null
}

function closeAddChild() {
  addingChild.value = false
  addChildTargetId.value = ''
  localError.value = null
}

async function submitAddChild() {
  const target = addChildTargetId.value.trim()
  if (!target) {
    localError.value = 'Enter a target entity UUID'
    return
  }
  if (target === props.entity.id) {
    localError.value = 'An entity cannot contain itself'
    return
  }
  addBusy.value = true
  localError.value = null
  try {
    await store.createLinkAction(props.entity.id, {
      target_id: target,
      link_type: CONTAINS,
    })
    closeAddChild()
  } catch (error) {
    localError.value = error instanceof Error ? error.message : 'Failed to create link'
  } finally {
    addBusy.value = false
  }
}

async function removeLink(link: EntityLink) {
  removingLinkId.value = link.id
  try {
    await store.deleteLinkAction(link.source_id, link)
  } catch (error) {
    console.error('Failed to delete link', error)
  } finally {
    removingLinkId.value = null
  }
}

function propertiesPreview(link: EntityLink): string | null {
  if (!link.properties || Object.keys(link.properties).length === 0) {
    return null
  }
  return JSON.stringify(link.properties)
}
</script>

<template>
  <div class="links-tab">
    <section class="link-section">
      <header class="link-section__header">
        <div>
          <div class="text-subtitle-1">Outgoing</div>
          <div class="text-caption text-medium-emphasis">
            Edges originating from this entity
          </div>
        </div>
        <v-btn
          size="small"
          color="primary"
          variant="tonal"
          prepend-icon="mdi-plus"
          @click="openAddChild"
        >
          Add child (contains)
        </v-btn>
      </header>

      <v-expand-transition>
        <v-card v-if="addingChild" class="add-card" variant="outlined">
          <v-card-text>
            <v-text-field
              v-model="addChildTargetId"
              label="Target entity UUID"
              variant="outlined"
              density="compact"
              :error-messages="localError ? [localError] : []"
              :disabled="addBusy"
              autofocus
              @keyup.enter="submitAddChild"
            />
            <div class="d-flex gap-2 justify-end">
              <v-btn variant="text" :disabled="addBusy" @click="closeAddChild">Cancel</v-btn>
              <v-btn color="primary" :loading="addBusy" @click="submitAddChild">Add link</v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-expand-transition>

      <v-alert
        v-if="!outgoingByType.length"
        type="info"
        variant="tonal"
        density="comfortable"
      >
        No outgoing links yet.
      </v-alert>

      <div
        v-for="group in outgoingByType"
        :key="`out-${group.type}`"
        class="link-group"
      >
        <div class="link-group__header">
          <v-chip size="small" variant="tonal" color="primary">{{ group.type }}</v-chip>
          <span class="text-caption text-medium-emphasis">
            {{ group.links.length }} link{{ group.links.length === 1 ? '' : 's' }}
          </span>
        </div>
        <v-list density="compact" class="link-list">
          <v-list-item
            v-for="link in group.links"
            :key="link.id"
            :subtitle="propertiesPreview(link) ?? undefined"
            class="link-row"
          >
            <template #prepend>
              <v-icon color="primary" class="mr-2">mdi-arrow-right-bold</v-icon>
            </template>
            <v-list-item-title class="link-id" @click="navigateToEntity(link.target_id)">
              {{ link.target_id }}
            </v-list-item-title>
            <template #append>
              <v-btn
                icon
                variant="text"
                color="primary"
                size="small"
                @click="navigateToEntity(link.target_id)"
              >
                <v-icon>mdi-open-in-new</v-icon>
              </v-btn>
              <v-btn
                v-if="group.type === CONTAINS"
                icon
                variant="text"
                color="error"
                size="small"
                :loading="removingLinkId === link.id"
                @click="removeLink(link)"
              >
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
      </div>
    </section>

    <v-divider class="my-4"></v-divider>

    <section class="link-section">
      <header class="link-section__header">
        <div>
          <div class="text-subtitle-1">Incoming</div>
          <div class="text-caption text-medium-emphasis">
            Edges pointing at this entity
          </div>
        </div>
      </header>

      <v-alert
        v-if="!incomingByType.length"
        type="info"
        variant="tonal"
        density="comfortable"
      >
        No incoming links yet.
      </v-alert>

      <div
        v-for="group in incomingByType"
        :key="`in-${group.type}`"
        class="link-group"
      >
        <div class="link-group__header">
          <v-chip size="small" variant="tonal" color="primary">{{ group.type }}</v-chip>
          <span class="text-caption text-medium-emphasis">
            {{ group.links.length }} link{{ group.links.length === 1 ? '' : 's' }}
          </span>
        </div>
        <v-list density="compact" class="link-list">
          <v-list-item
            v-for="link in group.links"
            :key="link.id"
            :subtitle="propertiesPreview(link) ?? undefined"
            class="link-row"
          >
            <template #prepend>
              <v-icon color="primary" class="mr-2">mdi-arrow-left-bold</v-icon>
            </template>
            <v-list-item-title class="link-id" @click="navigateToEntity(link.source_id)">
              {{ link.source_id }}
            </v-list-item-title>
            <template #append>
              <v-btn
                icon
                variant="text"
                color="primary"
                size="small"
                @click="navigateToEntity(link.source_id)"
              >
                <v-icon>mdi-open-in-new</v-icon>
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
      </div>
    </section>
  </div>
</template>

<style scoped>
.links-tab {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.link-section__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.link-group {
  margin-top: 12px;
}

.link-group__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.link-list {
  padding: 0;
  background: transparent;
}

.link-id {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  cursor: pointer;
  font-size: 0.9rem;
}

.add-card {
  margin-bottom: 12px;
}

.gap-2 {
  gap: 8px;
}
</style>
