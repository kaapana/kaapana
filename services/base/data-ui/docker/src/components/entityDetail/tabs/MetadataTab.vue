<script setup lang="ts">
import { ref, watch } from 'vue'
import MetadataAddCard from '@/components/entityDetail/metadata/MetadataAddCard.vue'
import MetadataEntriesAccordion from '@/components/entityDetail/metadata/MetadataEntriesAccordion.vue'
import type { DataEntity, MetadataEntry } from '@/types/domain'

const props = defineProps<{ entity: DataEntity; loading: boolean; dialogOpen: boolean }>()

const emit = defineEmits<{
  (e: 'save-metadata', payload: { id: string; entry: MetadataEntry }): void
  (e: 'delete-metadata', payload: { id: string; key: string }): void
}>()

const addMetadataVisible = ref(false)

watch(
  () => props.entity.id,
  () => {
    addMetadataVisible.value = false
  },
)

function forwardSave(payload: { id: string; entry: MetadataEntry }) {
  emit('save-metadata', payload)
}

function forwardDelete(payload: { id: string; key: string }) {
  emit('delete-metadata', payload)
}

function handleSubmitNew(entry: MetadataEntry) {
  emit('save-metadata', { id: props.entity.id, entry })
}
</script>

<template>
  <div>
    <div class="metadata-tab-actions">
      <v-btn color="primary" prepend-icon="mdi-plus" @click="addMetadataVisible = !addMetadataVisible">
        {{ addMetadataVisible ? 'Hide metadata form' : 'Add metadata' }}
      </v-btn>
    </div>

    <v-expand-transition>
      <div v-show="addMetadataVisible">
          <MetadataAddCard :loading="loading" :dialog-open="dialogOpen" @submit="handleSubmitNew" />
      </div>
    </v-expand-transition>

    <MetadataEntriesAccordion
      :entity="props.entity"
      :loading="loading"
      @save="forwardSave"
      @delete="forwardDelete"
    />
  </div>
</template>

<style scoped>
.metadata-tab-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}
</style>
