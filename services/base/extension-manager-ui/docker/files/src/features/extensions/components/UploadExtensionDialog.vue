<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import { fetchUploadLimits, uploadExtension } from '@/features/extensions/api'
import type { ExtensionManifestResponse } from '@/shared/types/apiSchemas'
import { notifyFailure, notifySuccess } from '@/shared/utils/notify'

const ARCHIVE_SUFFIX = '.tar.gz'
const BYTES_PER_MB = 1024 * 1024

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'uploaded', extension: ExtensionManifestResponse): void
}>()

const file = ref<File | null>(null)
const uploading = ref(false)
const progress = ref(0)
const maxBytes = ref<number | null>(null)
let opener: HTMLElement | null = null

const fileRules = [
  (value: File | File[] | null) => {
    const selected = Array.isArray(value) ? value[0] : value
    return (
      !selected ||
      selected.name.endsWith(ARCHIVE_SUFFIX) ||
      `Choose a ${ARCHIVE_SUFFIX} archive built with extensionctl.`
    )
  },
]
const maxMegabytes = computed(() =>
  maxBytes.value === null ? null : Math.floor(maxBytes.value / BYTES_PER_MB),
)
const tooLarge = computed(() => maxBytes.value !== null && (file.value?.size ?? 0) > maxBytes.value)
const archiveHint = computed(() =>
  maxMegabytes.value === null
    ? 'Upload an extension archive built with extensionctl.'
    : `Upload an extension archive built with extensionctl, at most ${maxMegabytes.value} MB.`,
)
const sizeErrors = computed(() =>
  tooLarge.value ? [`The archive is larger than ${maxMegabytes.value} MB.`] : [],
)
const canUpload = computed(
  () => Boolean(file.value?.name.endsWith(ARCHIVE_SUFFIX)) && !tooLarge.value && !uploading.value,
)
const progressPercent = computed(() => Math.round(progress.value * 100))
const processing = computed(() => uploading.value && progress.value >= 1)

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    file.value = null
    progress.value = 0
    void loadLimits()
  },
  { immediate: true },
)

async function loadLimits() {
  try {
    maxBytes.value = (await fetchUploadLimits()).max_bytes
  } catch {
    maxBytes.value = null
  }
}

function close() {
  if (uploading.value) return
  emit('update:modelValue', false)
  opener?.focus?.()
  opener = null
}

async function submit() {
  const selected = file.value
  if (!selected || !canUpload.value) return

  uploading.value = true
  progress.value = 0
  try {
    const extension = await uploadExtension(selected, (fraction) => (progress.value = fraction))
    const label = `${extension.manifest.name} ${extension.manifest.version}`
    notifySuccess('Extension uploaded', `${label} is now in the catalog and can be installed.`)
    emit('uploaded', extension)
    uploading.value = false
    close()
  } catch (err) {
    notifyFailure('Upload failed', `Could not upload ${selected.name}.`, err)
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <v-dialog
    :model-value="props.modelValue"
    max-width="560"
    :persistent="uploading"
    @update:model-value="(value: boolean) => !value && close()"
  >
    <v-card :elevation="5" data-testid="upload-dialog">
      <v-card-title class="d-flex align-start ga-2">
        <div class="flex-grow-1 text-wrap">
          <div class="text-h6">Upload extension</div>
          <div class="text-body-2 text-medium-emphasis">
            {{ archiveHint }} It is added to the Upload repository and can then be installed from
            the catalog.
          </div>
        </div>
        <v-btn
          :icon="kaapanaIcons.close"
          variant="text"
          size="small"
          aria-label="Close"
          :disabled="uploading"
          @click="close"
        />
      </v-card-title>

      <v-divider />

      <v-card-text>
        <v-form @submit.prevent="submit">
          <v-file-input
            v-model="file"
            :rules="fileRules"
            :error-messages="sizeErrors"
            :accept="`${ARCHIVE_SUFFIX},application/gzip`"
            :disabled="uploading"
            label="Extension archive (.tar.gz)"
            density="compact"
            variant="outlined"
            show-size
            data-testid="upload-file"
          />

          <div v-if="uploading" class="mt-2" data-testid="upload-progress">
            <v-progress-linear
              :model-value="progressPercent"
              :indeterminate="processing"
              color="primary"
              height="6"
              rounded
            />
            <div class="text-body-2 text-medium-emphasis mt-1">
              {{ processing ? 'Checking the archive…' : `Uploading… ${progressPercent}%` }}
            </div>
          </div>

          <div class="d-flex justify-end ga-2 mt-4">
            <v-btn variant="text" :disabled="uploading" @click="close">Cancel</v-btn>
            <v-btn
              type="submit"
              color="primary"
              variant="flat"
              :loading="uploading"
              :disabled="!canUpload"
              data-testid="upload-submit"
            >
              Upload
            </v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>
