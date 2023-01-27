<script setup lang="ts">
import { defineComponent } from 'vue'
</script>

<template>
  <h3>Available security providers:</h3>
  <div>{{securityProviders}}</div>
</template>

<script lang="ts">
export default defineComponent({
  name: "SecurityProviders",
  data() {
    return {
      securityProviders: "<loading>"
    };
  },

  async created() {
    const response = await fetch("https://httpbin.org/get?providers=Wazuh, StackRox");
    const data = await response.json();
    this.securityProviders = data.args.providers;
  }
});
</script>

