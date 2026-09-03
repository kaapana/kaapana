<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { kaapanaIcons } from '@/utils/galleryIcons'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    /** How many series the new dataset will contain, so the dialog can say what
     *  is actually being saved. */
    itemCount?: number
    /** Names already taken, so a collision is caught before the round trip. */
    existingNames?: string[]
    busy?: boolean
  }>(),
  { itemCount: 0, existingNames: () => [], busy: false },
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: [name: string, accessLevel: string]
  /** Unsaved work in this dialog, folded into the view's dirty state upstream. */
  'update:dirty': [dirty: boolean]
}>()

const ACCESS_LEVELS = [
  { value: 'private', title: 'Private', subtitle: 'Only you can see this dataset' },
  { value: 'project', title: 'Project', subtitle: 'Everyone in this project can see it' },
]

const name = ref('')
const accessLevel = ref('private')
const form = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
const nameField = ref<{ focus: () => void } | null>(null)
const discardDialog = ref(false)

// A pre-filled form is not dirty until the user changes it; here the form starts
// empty, so any name at all is unsaved work (guidelines, "Unsaved changes").
const dirty = computed(() => props.modelValue && name.value.trim() !== '')

// Validation says what is required and how to fix it, rather than "Invalid
// input" — and it is bound to the field, so Vuetify marks the control required
// instead of relying on an asterisk in the label (guidelines, "Validation").
const nameRules = [
  (value: string) =>
    !!value?.trim() || 'Enter a name for the dataset, for example: lung-segmentation.',
  (value: string) =>
    (value?.trim().length ?? 0) <= 64 || 'Use at most 64 characters.',
  (value: string) =>
    !props.existingNames.includes(value?.trim()) ||
    'A dataset with this name already exists. Choose a different name.',
]

function reset() {
  name.value = ''
  accessLevel.value = 'private'
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

watch(dirty, (value) => emit('update:dirty', value), { immediate: true })

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
  <!-- Medium (600px): a form and editing task. Escape and an outside click go
       through the same discard guard as Cancel, so they cancel safely rather
       than being ignored outright. -->
  <v-dialog
    :model-value="props.modelValue"
    max-width="600"
    @update:model-value="(value: boolean) => !value && requestClose()"
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
          ></v-text-field>
          <!-- Short, closed list with a description per option, so the effect of
               each choice is visible at the point of choosing. -->
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
    :consequences="[
      'The name and access level you entered will be lost.',
      'No dataset is created.',
    ]"
    cancel-label="Keep editing"
    confirm-label="Discard"
    @confirm="close"
  />
</template>
