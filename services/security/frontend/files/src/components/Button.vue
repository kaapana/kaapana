<script setup lang="ts">
import { defineComponent } from "vue"
</script>

<template>
  <button><div class="buttonContent"><slot></slot></div></button>
</template>

<script lang="ts">
export default defineComponent({
});
</script>

<style scoped>
button {
  width: 100%;
  border: var(--default-border);
  color: var(--color-text);
  background-color: var(--color-background);
  border-radius: var(--default-border-radius);
  height: 40px;
}

@media (min-width: 1024px) {
  button {
    max-width: 250px;
    width: fit-content;
  }
}

button:hover {
  color: var(--color-background);
  background-color: var(--color-text);
  cursor: pointer;
  box-shadow: 0px 5px 10px rgba(0,0,0,0.2);
}

.buttonContent {
  display: flex;
  width: 100%;
  padding: var(--default-padding);
  justify-content: center;
}
</style>