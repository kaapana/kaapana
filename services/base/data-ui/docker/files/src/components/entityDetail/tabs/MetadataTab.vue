<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import MetadataAddCard from '@/components/entityDetail/metadata/MetadataAddCard.vue'
import MetadataEntriesAccordion from '@/components/entityDetail/metadata/MetadataEntriesAccordion.vue'
import type { DataEntity } from '@/types/domain'
import { icons } from '@/utils/icons'

const props = defineProps<{ entity: DataEntity }>()
const emit = defineEmits<{ (e: 'dirty', value: boolean): void }>()

const addVisible = ref(false)
const addDirty = ref(false)
const entriesDirty = ref(false)

watch(
  () => props.entity.id,
  () => {
    addVisible.value = false
  },
)

watch(addVisible, (visible) => {
  if (!visible) addDirty.value = false
})

const dirty = computed(() => (addVisible.value && addDirty.value) || entriesDirty.value)
watch(dirty, (value) => emit('dirty', value), { immediate: true })
</script>

<template>
  <div>
    <div class="d-flex justify-end mb-4">
      <v-btn
        variant="text"
        color="primary"
        :prepend-icon="addVisible ? icons.close : icons.add"
        :aria-expanded="addVisible"
        @click="addVisible = !addVisible"
      >
        {{ addVisible ? 'Close new entry' : 'Add entry' }}
      </v-btn>
    </div>
    <MetadataAddCard
      v-if="addVisible"
      :entity="entity"
      @dirty="addDirty = $event"
      @added="addVisible = false"
    />
    <MetadataEntriesAccordion :entity="entity" @dirty="entriesDirty = $event" />
  </div>
</template>
