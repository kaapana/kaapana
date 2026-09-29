<template>
  <div>
    <iframe
      ref="iframe"
      :width="width"
      :height="height"
      :style="customStyle"
      class="no-border"
      :src="iFrameUrl"
      @load="onLoad"
    ></iframe>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'

withDefaults(
  defineProps<{
    iFrameUrl: string
    width?: string
    height?: string
    customStyle?: string
  }>(),
  {
    width: '100%',
    height: '100%',
    customStyle: '',
  },
)

const emit = defineEmits<{ ready: [] }>()

const iframe = ref<HTMLIFrameElement | null>(null)
let readyTimer: ReturnType<typeof setInterval> | null = null

function onLoad() {
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

onBeforeUnmount(() => {
  if (readyTimer) clearInterval(readyTimer)
  readyTimer = null
})
</script>

<style scoped lang="scss">
.no-border {
  border: none;
}
</style>
