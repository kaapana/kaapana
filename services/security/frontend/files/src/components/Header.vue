<script setup lang="ts">
import { ESize } from "@/types/enums";
import { defineComponent, type PropType } from "vue";
</script>

<template>
  <header>
    <div class="wrapper">
      <h1 v-if="size === undefined || size === EHeaderSize.LARGE">{{ title }}</h1>
      <h2 v-else-if="size === EHeaderSize.NORMAL">{{ title }}</h2>
      <h3 v-else>{{ title }}</h3>
    </div>
  </header>
</template>

<script lang="ts">
export type EHeaderSize = ESize.LARGE | ESize.NORMAL | ESize.SMALL;
export const EHeaderSize = {
  [ESize.LARGE]: ESize.LARGE,
  [ESize.NORMAL]: ESize.NORMAL,
  [ESize.SMALL]: ESize.SMALL
} as const;


export default defineComponent({
  props: {
    title: String,
    size: {
      type: String as PropType<EHeaderSize>,
      required: false
    }
  }
});
</script>

<style scoped>
h1 {
  font-weight: 500;
  font-size: 2.6rem;
  top: -10px;
}

h3 {
  font-size: 1.2rem;
}

.wrapper {
  width: 100%;
}

.wrapper h1,
.wrapper h2,
.wrapper h3 {
  text-align: left;
}

header {
  line-height: 1.5;
}


@media (min-width: 1024px) {
  header {
    display: flex;
    place-items: center;
    padding-right: calc(var(--section-gap) / 2);
  }
  header .wrapper {
    display: flex;
    flex-direction: column;
    place-items: flex-start;
    flex-wrap: wrap;
  }
}
</style>