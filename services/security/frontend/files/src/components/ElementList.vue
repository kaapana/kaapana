<script setup lang="ts">
import { ESize, EDirection } from '@/types/enums';
import { defineComponent, type PropType } from 'vue';


</script>

<template>
  <div class="list">
    <slot></slot>
  </div>
</template>

<script lang="ts">
type EElementListMargin = ESize.NORMAL | ESize.SMALL | ESize.NONE;
export const EElementListMargin = {
  [ESize.NORMAL]: ESize.NORMAL,
  [ESize.SMALL]: ESize.SMALL,
  [ESize.NONE]: ESize.NONE
} as const;

export default defineComponent({
  props: {
    margin: {
      type: String as PropType<EElementListMargin>,
      required: true
    },
    direction: {
      type: String as PropType<EDirection>,
      required: true
    }
  },
  computed: {
    listMargin() {
      if (this.margin === EElementListMargin.NORMAL) {
        return "var(--default-margin-value)";
      } else if (this.margin === EElementListMargin.SMALL) {
        return "calc(var(--default-margin-value)/2)";
      }

      return "0";
    },
    listFlexDirection() {
      if (this.direction == EDirection.HORIZONTAL) {
        return "row";
      }

      return "column";
    },
    gapOnMobile() {
      if (this.direction == EDirection.HORIZONTAL) {
        return "0";
      }

      return this.listMargin;
    }
  }
});
</script>

<style scoped>
.list {
  display: flex;
  flex-direction: column;
  gap: v-bind(gapOnMobile);
}

@media (min-width: 1024px) {
  .list {
    flex-direction: v-bind(listFlexDirection);
    gap: v-bind(listMargin);
    align-items: center;
  }
}
</style>