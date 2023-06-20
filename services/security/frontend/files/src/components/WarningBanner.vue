<script setup lang="ts">
import { defineComponent } from 'vue'
</script>

<template>
  <div class="banner">
    <div class="bannerContent">
      <slot></slot>
    </div>
  </div>
</template>

<script lang="ts">
export default defineComponent({

});
</script>

<style scoped>
.banner {
  height: 40px;
  width: 100%;
  background-color: var(--color-warning-background);
  color: var(--color-warning-text);
  border: var(--default-border);
  border-radius: var(--default-border-radius);
  display: flex;
  align-items: center;
}

.bannerContent {
  margin: var(--default-margin);
}
</style>