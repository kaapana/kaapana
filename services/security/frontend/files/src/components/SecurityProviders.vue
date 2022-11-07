<script setup lang="ts">
</script>

<template>
  <h3>Available security providers:</h3>
  <div>{{securityProviders}}</div>
</template>

<script lang="ts">
export default {
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
};
</script>

