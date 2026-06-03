<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useEntityStore } from '@/stores/entityStore'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'created', id: string): void
}>()

const store = useEntityStore()

const dialog = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const name = ref('')
const description = ref('')
const submitting = ref(false)
const errorMessage = ref<string | null>(null)

const canSubmit = computed(() => name.value.trim().length > 0 && !submitting.value)

watch(dialog, (open) => {
  if (open) {
    name.value = ''
    description.value = ''
    errorMessage.value = null
  }
})

async function submit() {
  if (!canSubmit.value) {
    return
  }
  submitting.value = true
  errorMessage.value = null
  try {
    const entity = await store.createDataset(name.value, description.value)
    emit('created', entity.id)
    dialog.value = false
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to create dataset'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <v-dialog v-model="dialog" max-width="520" close-on-esc>
    <v-card>
      <v-card-title class="text-h6">Create dataset</v-card-title>
      <v-card-text>
        <v-alert v-if="errorMessage" type="error" variant="tonal" density="compact" class="mb-3">
          {{ errorMessage }}
        </v-alert>
        <v-text-field
          v-model="name"
          label="Dataset name"
          placeholder="e.g. NSCLC Radiomics"
          autofocus
          :disabled="submitting"
          @keydown.enter.prevent="submit"
        />
        <v-textarea
          v-model="description"
          label="Description (optional)"
          rows="3"
          auto-grow
          :disabled="submitting"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" :disabled="submitting" @click="dialog = false">Cancel</v-btn>
        <v-btn color="primary" :loading="submitting" :disabled="!canSubmit" @click="submit">
          Create
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
