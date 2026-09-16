<script setup lang="ts">
withDefaults(defineProps<{ iFrameUrl: string; width?: string; height?: string }>(), {
  width: '100%',
  height: '100%',
})
</script>

<template>
  <div class="kaapana-iframe-container">
    <iframe
      :width="width"
      :height="height"
      class="no-border"
      :src="iFrameUrl"
    ></iframe>
  </div>
</template>

<style scoped lang="scss">
.no-border {
  border: none;
}

// The iframe's height="100%" needs a definite height on this wrapper; without
// one it collapses to the 150 px intrinsic default.
.kaapana-iframe-container {
  height: 100vh;
}
</style>
