<script setup lang="ts">
import Header from "@/components/Header.vue";
import { defineComponent } from 'vue'
</script>

<template>
  <Header title="Wazuh"/>
  <main>
    <p v-if="wazuhAgentAvailable===null">Loading Wazuh agents</p>
    <pre v-else>Wazuh agent available: {{ wazuhAgentAvailable }}</pre>
  </main>
</template>

<script lang="ts">
export default defineComponent({
  data() {
    return {
      wazuhAgentAvailable: null
    };
  },
  methods: {
    async checkWazuhAgents() {
      const response = await fetch(window.location.origin + "/security/api/extension/wazuh/agent-installed");
      if (response.status !== 200) {
        throw new Error("Unexpected response from backend");
      }
      const json = await response.json();
      this.wazuhAgentAvailable = json["agent_installed"];
    }
  },
  async mounted() {
    await this.checkWazuhAgents();
  }
});
</script>