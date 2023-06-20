<script setup lang="ts">
import { ESize } from '@/types/enums';
import { defineComponent, type PropType } from 'vue';
</script>

<template>
  <div class="group">
    <slot></slot>
  </div>
</template>

<script lang="ts">
type EGroupPadding = ESize.NORMAL | ESize.SMALL;
export const EGroupPadding = {
  [ESize.NORMAL]: ESize.NORMAL,
  [ESize.SMALL]: ESize.SMALL
} as const;

export default defineComponent({
  props: {
    alternativeColorScheme: {
      type: Boolean,
      required: false
    },
    paddingSize: {
      type: String as PropType<EGroupPadding>,
      required: false,
      default: ESize.NORMAL
    }
  },
  computed: {
    backgroundColor() {
      if (this.alternativeColorScheme) {
        return "var(--color-background)";
      }

      return "var(--color-background-soft)";
    },
    computedPaddingSize() {
      if (this.paddingSize === EGroupPadding.NORMAL) {
        return "var(--default-padding-value)";
      }

      return "calc(var(--default-padding-value) / 2) var(--default-padding-value)";
    }
  }
});
</script>

<style scoped>
.group {
  width: 100%;
  height: fit-content;
  padding: v-bind(computedPaddingSize);
  border: var(--default-border);
  border-radius: var(--default-border-radius);
  background-color: v-bind(backgroundColor);
}
</style>