<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ConfirmDialog } from '@kaapana/base-ui'
import { useFocusReturn } from '@/composables/useFocusReturn'
import { kaapanaIcons } from '@/utils/galleryIcons'
import type { Dataset } from '@/types'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    itemCount?: number
    /** Names are unique per access level. The list holds the user's own private datasets. */
    existingDatasets?: Pick<Dataset, 'name' | 'access_level'>[]
    busy?: boolean
  }>(),
  { itemCount: 0, existingDatasets: () => [], busy: false },
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: [name: string, accessLevel: string]
  'update:dirty': [dirty: boolean]
}>()

const ACCESS_LEVELS = [
  { value: 'private', title: 'Private', subtitle: 'Only you can see this dataset' },
  { value: 'project', title: 'Project', subtitle: 'Everyone in this project can see it' },
]

const DEFAULT_ACCESS_LEVEL = 'private'

const name = ref('')
const accessLevel = ref(DEFAULT_ACCESS_LEVEL)
const form = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
const nameField = ref<{ focus: () => void; validate: () => Promise<string[]> } | null>(null)
const discardDialog = ref(false)
const { restoreFocus } = useFocusReturn(() => props.modelValue)

const dirty = computed(
  () =>
    props.modelValue && (name.value.trim() !== '' || accessLevel.value !== DEFAULT_ACCESS_LEVEL),
)

const nameRules = [
  (value: string) =>
    !!value?.trim() || 'Enter a name for the dataset, for example: lung-segmentation.',
  (value: string) =>
    (value?.trim().length ?? 0) <= 64 || 'Use at most 64 characters.',
  (value: string) =>
    !props.existingDatasets.some(
      (dataset) => dataset.name === value?.trim() && dataset.access_level === accessLevel.value,
    ) || `A ${accessLevel.value} dataset with this name already exists. Choose a different name.`,
]

function reset() {
  name.value = ''
  accessLevel.value = DEFAULT_ACCESS_LEVEL
}

async function submit() {
  const result = await form.value?.validate()
  if (!result?.valid) return
  emit('save', name.value.trim(), accessLevel.value)
}

/** Escape, an outside click, or Cancel — all discard the same work, so all go
 *  through the same guard. */
function requestClose() {
  if (dirty.value) {
    discardDialog.value = true
    return
  }
  close()
}

function close() {
  discardDialog.value = false
  reset()
  emit('update:modelValue', false)
}

function onDiscardLeave() {
  if (props.modelValue) nameField.value?.focus()
  else restoreFocus()
}

watch(dirty, (value) => emit('update:dirty', value), { immediate: true })

// On an access-level change, recheck whether the name is taken at that level.
watch(accessLevel, () => {
  if (name.value.trim()) nameField.value?.validate()
})

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) {
      reset()
      return
    }
    await nextTick()
    nameField.value?.focus()
  },
)
</script>

<template>
  <v-dialog
    :model-value="props.modelValue"
    max-width="600"
    :persistent="props.busy"
    @update:model-value="(value: boolean) => !value && requestClose()"
    @after-leave="restoreFocus"
  >
    <v-card :elevation="5">
      <v-card-title class="text-h6">Save selection as dataset</v-card-title>
      <v-card-subtitle v-if="props.itemCount" class="text-body-2 text-medium-emphasis pb-2">
        {{ props.itemCount }} series will be saved.
      </v-card-subtitle>
      <v-card-text>
        <v-form ref="form" validate-on="blur" @submit.prevent="submit">
          <v-text-field
            ref="nameField"
            v-model="name"
            label="Name"
            :rules="nameRules"
            required
            clearable
            autofocus
            @keydown.enter.prevent="submit"
          ></v-text-field>
          <v-select
            v-model="accessLevel"
            label="Access level"
            :items="ACCESS_LEVELS"
            item-value="value"
            item-title="title"
          >
            <template v-slot:item="{ props: itemProps, item }">
              <v-list-item v-bind="itemProps" :subtitle="item.raw.subtitle" />
            </template>
          </v-select>
        </v-form>
      </v-card-text>
      <v-divider></v-divider>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" :disabled="props.busy" @click="requestClose">Cancel</v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :loading="props.busy"
          :disabled="props.busy"
          :prepend-icon="kaapanaIcons.save"
          @click="submit"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <ConfirmDialog
    v-model="discardDialog"
    title="Discard this dataset?"
    text="The name and access level you entered will be lost. No dataset is created."
    cancel-text="Keep editing"
    confirm-text="Discard"
    color="error"
    @confirm="close"
    @after-leave="onDiscardLeave"
  />
</template>
