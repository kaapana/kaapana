<script setup lang="ts">
import { defineComponent } from "vue";
import Divider from '@/components/Divider.vue';
import Button from '@/components/Button.vue';
</script>

<template>
  <div>
    <slot v-if="err" name="error" >
      <div class="error-wrapper">
        <h2>An error occured</h2>
        <p>{{ err }}</p>
        <p>in &lt; {{ component }} /&gt;</p>
        <p>Further information: {{ info }}</p>
      </div>
      <Divider></Divider>
      <div class="buttons">
        <Button @:click="reload" class="button">Reload</Button>
        <Button @:click="goBack" class="button">Go back</Button>
      </div>
    </slot>
    <slot v-else></slot>
  </div>
</template>

<script lang="ts">
interface ErrorBoundaryData {
  err: unknown;
  component: string | undefined;
  info: string | null;
}

export default defineComponent({
  name: "ErrorBoundary",
  data(): ErrorBoundaryData {
    return {
      err: false,
      component: undefined,
      info: null
    };
  },
  methods: {
    reload() {
      window.location.reload();
    },
    goBack() {
      window.history.back();
    }
  },
  errorCaptured(err, vm, info) {
    this.err = err;
    this.component = vm ? vm.$options.__name : undefined;
    this.info = info;
    return true; // propagate error
  }
});
</script>

<style scoped>
.error-wrapper {
  display: flex;
  flex-direction: column;
}

.buttons {
  display: flex;
  gap: 20px;
}

.button {
  min-width: 150px;
}

h2 {
  margin-bottom: 20px;
}
</style>
