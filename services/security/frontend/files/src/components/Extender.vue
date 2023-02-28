<script setup lang="ts">
import { defineComponent, type PropType } from 'vue';
</script>

<template>
  <div @click="onClick();" class="extender">
    <div class="extender-symbol">►</div>
  </div>
</template>

<script lang="ts">
export default defineComponent({
  props: {
    onClick: {
      type: Function as PropType<() => void>,
      required: false,
      default: () => {}
    },
    reverseIcon: {
      type: Boolean,
      required: false,
      default: false
    }
  },
  computed: {
    iconRotation() {
      return this.reverseIcon ? "-90deg" : "90deg"
    }
  }
});
</script>

<style scoped>
.extender {
  width: 100%;
  height: 100%;
  min-height: 25px;
  display: flex;
  justify-content: center;
  backdrop-filter: brightness(0.8);
  border-radius: 5px;
  cursor: pointer;
}

.extender-symbol {
  transform: scale(120%, 75%) rotate(v-bind(iconRotation));
}
</style>