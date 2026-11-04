<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { kaapanaIcons } from '@kaapana/base-ui'
import { uploadExtension } from '@/features/extensions/api'
import type { InstalledExtension } from '@/shared/types/apiSchemas'
import { notifyFailure, notifySuccess } from '@/shared/utils/notify'

const ARCHIVE_SUFFIX = '.tar.gz'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'uploaded', extension: InstalledExtension): void
}>()

const file = ref<File | null>(null)
const uploading = ref(false)
const progress = ref(0)
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
const canInstall = computed(
  () => Boolean(file.value?.name.endsWith(ARCHIVE_SUFFIX)) && !uploading.value,
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
  },
  { immediate: true },
)

function close() {
  if (uploading.value) return
  emit('update:modelValue', false)
  opener?.focus?.()
  opener = null
}

async function install() {
  const selected = file.value
  if (!selected || !canInstall.value) return

  uploading.value = true
  progress.value = 0
  try {
    const extension = await uploadExtension(selected, (fraction) => (progress.value = fraction))
    const label = `${extension.manifest.name} ${extension.manifest.version}`
    notifySuccess('Installation started', `${label} is being installed from ${selected.name}.`)
    emit('uploaded', extension)
    uploading.value = false
    close()
  } catch (err) {
    notifyFailure('Installation failed to start', `Could not install ${selected.name}.`, err)
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
          <div class="text-h6">Install from file</div>
          <div class="text-body-2 text-medium-emphasis">
            Install an extension archive built with extensionctl, without a repository.
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
        <v-form @submit.prevent="install">
          <v-file-input
            v-model="file"
            :rules="fileRules"
            :accept="`${ARCHIVE_SUFFIX},application/gzip`"
            :disabled="uploading"
            label="Extension archive (.tar.gz)"
            density="compact"
            variant="outlined"
            prepend-icon=""
            prepend-inner-icon="mdi-paperclip"
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
              :disabled="!canInstall"
              data-testid="upload-submit"
            >
              Install
            </v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>
