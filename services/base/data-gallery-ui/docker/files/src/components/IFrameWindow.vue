<template>
  <div :class="fullSize ? 'kaapana-iframe-container-side-navigation' : ''">
    <iframe
      ref="iframe"
      :width="width"
      :height="height"
      :style="customStyle"
      :class="fullSize ? 'kaapana-side-navigation' : ''"
      class="no-border"
      :src="iFrameUrl"
      @load="setIframeUrl"
    ></iframe>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

withDefaults(
  defineProps<{
    iFrameUrl: string
    fullSize?: boolean
    width?: string
    height?: string
    customStyle?: string
  }>(),
  {
    fullSize: true,
    width: '100%',
    height: '100%',
    customStyle: '',
  },
)

const emit = defineEmits<{ load: []; ready: [] }>()

const iframe = ref<HTMLIFrameElement | null>(null)
const trackedUrl = ref('')
let readyTimer: ReturnType<typeof setInterval> | null = null

function setIframeUrl() {
  trackedUrl.value = iframe.value?.contentWindow?.location.href ?? ''
  emit('load')
  // "load" fires when the embedded app's document is parsed, long before e.g.
  // OHIF paints anything. For same-origin content, report ready once a canvas
  // is rendered; fall back to ready on timeout or cross-origin frames.
  if (readyTimer) clearInterval(readyTimer)
  const start = Date.now()
  readyTimer = setInterval(() => {
    let ready = false
    try {
      ready = !!iframe.value?.contentDocument?.querySelector('canvas')
    } catch {
      ready = true
    }
    if (ready || Date.now() - start > 20000) {
      if (readyTimer) clearInterval(readyTimer)
      readyTimer = null
      emit('ready')
    }
  }, 300)
}

function refreshIFrame() {
  if (iframe.value) iframe.value.src = trackedUrl.value
}

function getIframeUrl() {
  return iframe.value?.contentWindow?.location
}

defineExpose({ refreshIFrame, getIframeUrl })
</script>

<style scoped lang="scss">
.no-border {
  border: none;
}
</style>
