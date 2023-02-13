<script setup lang="ts">
import { defineComponent } from "vue";
import { useThemeStore } from "@/stores/theme";

const themeStore = useThemeStore();
</script>

<template>
  <header>
    <div class="wrapper">
      <h1>{{ title }}</h1>
      <slot></slot>
    </div>
  </header>
</template>

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

<script lang="ts">
export default defineComponent({
  props: {
    title: String,
    divider: Boolean
  }
});
</script>
