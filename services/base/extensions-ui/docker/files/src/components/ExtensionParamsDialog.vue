<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { kaapanaIcons } from '@/utils/extensionIcons'

export interface ExtensionParam {
  type: 'string' | 'bool' | 'boolean' | 'list_single' | 'list_multi' | 'group_name' | 'doc'
  default?: any
  definition?: string
  value?: any[]
  help?: string
  title?: string
  html?: string
}

const props = defineProps<{
  modelValue: boolean
  /** Display name of the extension being configured. */
  extensionName: string
  /** "Install" for a single-install extension, "Launch" for a multi-installable one. */
  submitLabel: string
  params: Record<string, ExtensionParam>
  busy?: boolean
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'update:dirty', value: boolean): void
  (event: 'submit', values: Record<string, any>): void
}>()

const form = ref<any>(null)
// Where focus was when the dialog opened; a model-driven dialog gives Vuetify no
// activator to return focus to on close.
let opener: HTMLElement | null = null
const values = ref<Record<string, any>>({})
// The values the dialog opened with. "A pre-filled form is not dirty until the
// user changes it", so dirtiness is a comparison against this, not a flag set
// by the first keystroke.
const initialValues = ref<Record<string, any>>({})
const showDiscardConfirm = ref(false)

function defaultsFor(params: Record<string, ExtensionParam>): Record<string, any> {
  const next: Record<string, any> = {}
  for (const key of Object.keys(params ?? {})) next[key] = params[key]?.default
  return next
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    opener = document.activeElement as HTMLElement | null
    // Reset on every open so one extension's parameters cannot leak into the next.
    initialValues.value = defaultsFor(props.params)
    values.value = { ...initialValues.value }
  },
  { immediate: true },
)

const isDirty = computed(
  () =>
    props.modelValue &&
    JSON.stringify(values.value) !== JSON.stringify(initialValues.value),
)

// The portal protects shell-controlled navigation (project switch, view
// replacement) with this; it does not replace the discard confirmation below,
// which covers the actions this view itself controls.
watch(isDirty, (dirty) => emit('update:dirty', dirty), { immediate: true })

const entries = computed(() =>
  Object.entries(props.params ?? {}).map(([key, param]) => ({ key, param })),
)

function fieldLabel(key: string, param: ExtensionParam): string {
  return param.definition ? `${param.definition} (${key})` : String(key)
}

// The guidelines govern how a validation message is WORDED — "state what is
// required and how to fix the value" — not which values are acceptable. So the
// wording improves on "Empty string field" while each predicate stays byte-for-
// byte the one it replaced; tightening them here would block configurations
// that used to install.
function requiredText(key: string, param: ExtensionParam) {
  return (value: any) =>
    (value && value.length > 0) || `Enter a value for ${fieldLabel(key, param)}.`
}

function requiredChoice(key: string, param: ExtensionParam) {
  return (value: any) =>
    (value && value.length > 0) || `Choose an option for ${fieldLabel(key, param)}.`
}

function requiredChoices(key: string, param: ExtensionParam) {
  return (value: any) =>
    (value && value.length > 0) || `Choose at least one option for ${fieldLabel(key, param)}.`
}

function close() {
  emit('update:modelValue', false)
  opener?.focus?.()
  opener = null
}

/** Escape, an outside click, or Cancel. Never discards edits silently. */
function requestClose() {
  if (isDirty.value) {
    showDiscardConfirm.value = true
    return
  }
  close()
}

function discardChanges() {
  close()
}

async function submit() {
  const result = await form.value?.validate()
  if (result && !result.valid) return

  // Every key with a defined value, matching the original payload. `group_name`
  // carries its title here and `doc` has no default (so it drops out) — that is
  // what the backend has always received, and narrowing it is not this change's
  // business.
  const submitted: Record<string, any> = {}
  for (const [key, value] of Object.entries(values.value)) {
    if (value !== undefined) submitted[key] = value
  }
  emit('submit', submitted)
  close()
}
</script>

<template>
  <!-- Medium (600px): forms and editing tasks. Not `persistent`: Escape and an
       outside click are allowed, but routed through the discard confirmation. -->
  <v-dialog
    :model-value="props.modelValue"
    max-width="600"
    scrollable
    @update:model-value="(value: boolean) => !value && requestClose()"
  >
    <v-card :elevation="5">
      <v-card-title class="d-flex align-center ga-2">
        <span class="text-h6 text-truncate">Configure {{ props.extensionName }}</span>
        <v-spacer />
        <v-btn
          :icon="kaapanaIcons.close"
          variant="text"
          size="small"
          aria-label="Close without installing"
          @click="requestClose"
        />
      </v-card-title>

      <v-divider />

      <v-card-text>
        <v-form ref="form" @submit.prevent="submit">
          <template v-for="{ key, param } in entries" :key="key">
            <div v-if="param.type === 'group_name'" class="text-subtitle-1 font-weight-medium mt-4 mb-2">
              {{ param.default }}
            </div>

            <div v-else-if="param.type === 'doc'" class="mt-4 mb-2">
              <div class="text-subtitle-1 font-weight-medium mb-1">{{ param.title }}</div>
              <!-- eslint-disable-next-line vue/no-v-html -->
              <div v-if="param.html" class="text-body-2" v-html="param.html"></div>
            </div>

            <v-text-field
              v-else-if="param.type === 'string'"
              v-model="values[key]"
              :label="fieldLabel(key, param)"
              :rules="[requiredText(key, param)]"
              validate-on="blur"
              variant="outlined"
              density="comfortable"
              clearable
            >
              <template v-if="param.help" #append>
                <v-tooltip location="right">
                  <template #activator="{ props: tooltipProps }">
                    <v-icon
                      v-bind="tooltipProps"
                      :icon="kaapanaIcons.help"
                      :aria-label="`Help for ${fieldLabel(key, param)}`"
                    />
                  </template>
                  <!-- eslint-disable-next-line vue/no-v-html -->
                  <div v-html="param.help"></div>
                </v-tooltip>
              </template>
            </v-text-field>

            <v-checkbox
              v-else-if="param.type === 'bool' || param.type === 'boolean'"
              v-model="values[key]"
              :label="fieldLabel(key, param)"
              color="primary"
              density="comfortable"
              hide-details
              class="mb-4"
            >
              <template v-if="param.help" #append>
                <v-tooltip location="right">
                  <template #activator="{ props: tooltipProps }">
                    <v-icon
                      v-bind="tooltipProps"
                      :icon="kaapanaIcons.help"
                      :aria-label="`Help for ${fieldLabel(key, param)}`"
                    />
                  </template>
                  <!-- eslint-disable-next-line vue/no-v-html -->
                  <div v-html="param.help"></div>
                </v-tooltip>
              </template>
            </v-checkbox>

            <v-select
              v-else-if="param.type === 'list_single'"
              v-model="values[key]"
              :items="param.value"
              :label="fieldLabel(key, param)"
              :rules="[requiredChoice(key, param)]"
              validate-on="blur"
              variant="outlined"
              density="comfortable"
              clearable
            >
              <template v-if="param.help" #append>
                <v-tooltip location="right">
                  <template #activator="{ props: tooltipProps }">
                    <v-icon
                      v-bind="tooltipProps"
                      :icon="kaapanaIcons.help"
                      :aria-label="`Help for ${fieldLabel(key, param)}`"
                    />
                  </template>
                  <!-- eslint-disable-next-line vue/no-v-html -->
                  <div v-html="param.help"></div>
                </v-tooltip>
              </template>
            </v-select>

            <v-select
              v-else-if="param.type === 'list_multi'"
              v-model="values[key]"
              multiple
              chips
              :items="param.value"
              :label="fieldLabel(key, param)"
              :rules="[requiredChoices(key, param)]"
              validate-on="blur"
              variant="outlined"
              density="comfortable"
              clearable
            >
              <template v-if="param.help" #append>
                <v-tooltip location="right">
                  <template #activator="{ props: tooltipProps }">
                    <v-icon
                      v-bind="tooltipProps"
                      :icon="kaapanaIcons.help"
                      :aria-label="`Help for ${fieldLabel(key, param)}`"
                    />
                  </template>
                  <!-- eslint-disable-next-line vue/no-v-html -->
                  <div v-html="param.help"></div>
                </v-tooltip>
              </template>
            </v-select>
          </template>
        </v-form>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <!-- Secondary: a safe dismissal. Not `error` — cancelling destroys nothing. -->
        <v-btn variant="text" @click="requestClose">Cancel</v-btn>
        <!-- The one primary action of this dialog. -->
        <v-btn color="primary" variant="flat" :loading="props.busy" @click="submit">
          {{ props.submitLabel }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <ConfirmDialog
    v-model="showDiscardConfirm"
    tone="destructive"
    :title="`Discard the configuration for ${props.extensionName}?`"
    :consequences="[
      'The values you entered in this form will be lost.',
      'Nothing is installed, and the extension stays available to configure again.',
    ]"
    confirm-label="Discard changes"
    cancel-label="Keep editing"
    @confirm="discardChanges"
  />
</template>
