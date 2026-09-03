<script setup lang="ts">
import { computed, onBeforeMount, onBeforeUnmount, ref } from 'vue'
import { downloadDatasets } from '@/common/api.service'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { galleryIcons } from '@/utils/galleryIcons'

const MAX_DOWNLOADABLE_ITEM = 20

const props = withDefaults(defineProps<{ selectedSeries?: string[] | null }>(), {
  selectedSeries: () => [],
})

const downloading = ref(false)
const confirmDialog = ref(false)

const count = computed(() => props.selectedSeries?.length ?? 0)
const tooManyItems = computed(() => count.value > MAX_DOWNLOADABLE_ITEM)
const canDownload = computed(() => count.value > 0 && !tooManyItems.value && !downloading.value)

// A disabled action explains why it is unavailable when the reason is not
// obvious (guidelines, "Unavailable actions").
const status = computed(() => {
  if (downloading.value) return `Downloading ${count.value} series…`
  if (count.value === 0) return 'Select at least one series to download'
  if (tooManyItems.value) {
    return `Too many series selected (${count.value}). Download at most ${MAX_DOWNLOADABLE_ITEM} at a time, or use the "download-selected-files" workflow for larger amounts.`
  }
  return `Download ${count.value} series`
})

async function startDownload() {
  confirmDialog.value = false
  if (!props.selectedSeries?.length) return
  downloading.value = true
  try {
    await downloadDatasets(props.selectedSeries.join(';'))
  } catch {
    // downloadDatasets already reported what failed and what it means.
  } finally {
    downloading.value = false
  }
}

// Prevent reloading the window while downloading.
function preventReload(event: BeforeUnloadEvent) {
  if (downloading.value) {
    event.preventDefault()
    event.returnValue = '' // Required for Chrome
  }
}

onBeforeMount(() => {
  window.addEventListener('beforeunload', preventReload)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', preventReload)
})
</script>

<template>
  <v-tooltip location="bottom" :text="status">
    <template v-slot:activator="{ props: activator }">
      <!-- One button throughout: the handler sits on the button (not on the
           icon inside it, which no keyboard can reach) and progress shows on
           the control that started the download. -->
      <span v-bind="activator">
        <v-btn
          :icon="galleryIcons.download"
          :aria-label="status"
          variant="text"
          color="primary"
          :disabled="!canDownload"
          :loading="downloading"
          @click="confirmDialog = true"
        />
      </span>
    </template>
  </v-tooltip>

  <!-- Reversible, but it can take a long time and a lot of bandwidth and disk,
       so it states the scope before it starts. Not destructive, so the
       confirmation is `primary`, not `error` (guidelines, "High-impact
       actions"). -->
  <ConfirmDialog
    v-model="confirmDialog"
    tone="high-impact"
    :title="`Download ${count} series?`"
    :consequences="[
      'The series are packaged into a single zip file before the download starts, which may take several minutes.',
      'The transfer uses network bandwidth and local storage for as long as it runs.',
      'Reloading or closing this view while the download runs cancels it.',
    ]"
    confirm-label="Download"
    :busy="downloading"
    @confirm="startDownload"
  />
</template>
