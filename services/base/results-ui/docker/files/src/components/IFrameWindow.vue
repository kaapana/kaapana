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

const iframe = ref<HTMLIFrameElement | null>(null)
const trackedUrl = ref<unknown>('')

function setIframeUrl() {
  trackedUrl.value = iframe.value?.contentWindow?.location
}

function refreshIFrame() {
  if (iframe.value) iframe.value.src = String(trackedUrl.value)
}

function getIframeUrl() {
  return iframe.value?.contentWindow?.location
}

defineExpose({ refreshIFrame, getIframeUrl })
</script>

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

<style scoped lang="scss">
.no-border {
  border: none;
}

// The iframe's height="100%" needs a definite height on this wrapper; without
// one it collapses to the 150 px intrinsic default.
.kaapana-iframe-container-side-navigation {
  height: 100vh;
}
</style>
