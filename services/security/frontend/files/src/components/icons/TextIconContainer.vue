<script setup lang="ts">
import { defineComponent } from 'vue';
</script>

<template>
  <div class="container">
    <strong v-if="text !== undefined">{{ text }}</strong>
  </div>
</template>

<script lang="ts">
export default defineComponent({
  props: {
    text: {
      type: String,
      required: false
    },
    containerColor: {
      type: String,
      required: true
    }
  }

});
</script>

<style scoped>
.container {
  background-color: v-bind(containerColor);
  color: var(--color-text-dark);
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
}
</style>