<script setup lang="ts">
import { useFocusReturn } from '@/composables/useFocusReturn'
import { ref, watch } from 'vue'
import SchemaManager from '@/components/SchemaManager.vue'
import { icons } from '@/utils/icons'

const model = defineModel<boolean>({ required: true })
const restoreFocus = useFocusReturn(model)
defineProps<{ initialKey?: string | null }>()
const emit = defineEmits<{ (e: 'dirty', value: boolean): void }>()

const manager = ref<InstanceType<typeof SchemaManager> | null>(null)

function close() {
  if (!manager.value) {
    model.value = false
    return
  }
  manager.value.guarded(() => {
    model.value = false
  })
}

watch(model, (open) => {
  if (!open) emit('dirty', false)
})
</script>

<template>
  <v-dialog
    :model-value="model"
    max-width="900"
    @update:model-value="(open: boolean) => (open ? undefined : close())"
    @after-leave="restoreFocus"
  >
    <v-card :elevation="5">
      <v-card-title class="d-flex align-center">
        <span class="mr-auto">Metadata schemas</span>
        <v-btn :icon="icons.close" variant="text" aria-label="Close" @click="close" />
      </v-card-title>
      <v-card-text>
        <SchemaManager
          v-if="model"
          ref="manager"
          :initial-key="initialKey"
          @dirty="emit('dirty', $event)"
        />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>
