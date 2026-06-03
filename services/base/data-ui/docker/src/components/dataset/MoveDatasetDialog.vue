<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useEntityStore } from '@/stores/entityStore'

const props = defineProps<{
  modelValue: boolean
  datasetId: string | null
  datasetName: string
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'moved'): void
}>()

const store = useEntityStore()

const ROOT_VALUE = '__root__'

const dialog = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const target = ref<string>(ROOT_VALUE)
const targets = ref<{ id: string; name: string }[]>([])
const loadingTargets = ref(false)
const submitting = ref(false)
const errorMessage = ref<string | null>(null)

const targetItems = computed(() => [
  { title: 'Root (top level — no parent)', value: ROOT_VALUE },
  ...targets.value.map((t) => ({ title: t.name, value: t.id })),
])

watch(dialog, async (open) => {
  if (!open || !props.datasetId) {
    return
  }
  target.value = ROOT_VALUE
  errorMessage.value = null
  loadingTargets.value = true
  try {
    targets.value = await store.fetchMovableTargets(props.datasetId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load target datasets'
  } finally {
    loadingTargets.value = false
  }
})

async function submit() {
  if (!props.datasetId || submitting.value) {
    return
  }
  submitting.value = true
  errorMessage.value = null
  try {
    await store.moveDataset(props.datasetId, target.value === ROOT_VALUE ? null : target.value)
    emit('moved')
    dialog.value = false
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to move dataset'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <v-dialog v-model="dialog" max-width="520" close-on-esc>
    <v-card>
      <v-card-title class="text-h6">Move dataset</v-card-title>
      <v-card-text>
        <p class="text-body-2 mb-3">
          Move <strong>{{ datasetName }}</strong> under another dataset, or to the top level.
          Its current parent link is replaced.
        </p>
        <v-alert v-if="errorMessage" type="error" variant="tonal" density="compact" class="mb-3">
          {{ errorMessage }}
        </v-alert>
        <v-select
          v-model="target"
          :items="targetItems"
          :loading="loadingTargets"
          label="Destination"
          :disabled="submitting"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" :disabled="submitting" @click="dialog = false">Cancel</v-btn>
        <v-btn color="primary" :loading="submitting" @click="submit">Move</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
