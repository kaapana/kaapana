<script setup lang="ts">
import Header from "@/components/Header.vue";
import WarningBanner from "@/components/WarningBanner.vue";
import Button from "@/components/Button.vue"
import { defineComponent } from 'vue'
import { useWazuhStore, type AgentInformationMap } from "@/stores/wazuh";
import { mapWritableState } from "pinia";
import type { IAgentInformation } from "@/types/wazuh";
import Group from "@/components/Group.vue";
import ExternalArrow from '@/components/icons/ExternalArrow.vue';

</script>

<template>
  <div class="header">
    <Header title="Wazuh" :divider="true"></Header>
    <template v-if="wazuhUrl !== null">
      <Button @:click="openWazuhDashboard" class="middleButton"><ExternalArrow></ExternalArrow>Wazuh Dashboard</Button>
      <Button @:click="addNewAgent">+ Add new Agent</Button>
    </template>
  </div>
  <main>
    <div v-if="wazuhAgentAvailable === null">Checking for installed agents...</div>
    <div v-else-if="wazuhAgentAvailable === true">
      <Group v-if="agentInformation === null">Loading agent information...</Group>
      <RouterView v-else></RouterView>
    </div>
    <WarningBanner v-else>No installed agent was found, please add one to the system you want to monitor.</WarningBanner>
  </main>
</template>

<script lang="ts">
interface IViewData {
  wazuhAgentAvailable: boolean | null;
  wazuhUrl: string | null;
}

export default defineComponent({
  data(): IViewData {
    return {
      wazuhAgentAvailable: null,
      wazuhUrl: null
    };
  },
  computed: {
    ...mapWritableState(useWazuhStore, ["agentInformation"])
  },
  methods: {
    async checkWazuhAgentInstalled() {
      const response = await fetch(window.location.origin + "/security/api/providers/wazuh/agent-installed");
      if (response.status !== 200) {
        throw new Error("Unexpected response from backend");
      }
      const json = await response.json();
      this.wazuhAgentAvailable = json["data"];
    },
    async getAgentInformation() {
      if (this.agentInformation) {
        return;
      }
      const response = await fetch(window.location.origin + "/security/api/providers/wazuh/agents");
      if (response.status !== 200) {
        throw new Error("Unexpected response from backend");
      }
      const json = await response.json();
      if (json["data"] === null) {
        this.agentInformation = new Map();
        return;
      }
      this.agentInformation = json["data"].reduce((acc: AgentInformationMap, agent: IAgentInformation) => {
        acc.set(agent.id, agent);
        return acc;
      }, new Map());
    },
    async getWazuhUrl() {
      const response = await fetch(window.location.origin + "/security/api/providers/wazuh/url");
      if (response.status !== 200) {
        throw new Error("Unexpected response from backend");
      }
      const json = await response.json();
      this.wazuhUrl = json["data"];
    },
    openWazuhDashboard() {
      if (this.wazuhUrl) {
        window.open(this.wazuhUrl, "_blank")?.focus();
      }
    },
    addNewAgent() {
      window.open("https://documentation.wazuh.com/current/installation-guide/wazuh-agent/index.html", "_blank")?.focus();
    }
  },
  async mounted() {
    const agent_installed_promise = this.checkWazuhAgentInstalled();
    const agent_information_promise = this.getAgentInformation();
    const wazuh_url_promise = this.getWazuhUrl();
    await Promise.all([agent_installed_promise, agent_information_promise, wazuh_url_promise]);
  }
});
</script>

<style scoped>
.header {
  display: flex;
  width: 100%;
  flex-direction: column;
  margin-bottom: var(--default-margin-value);
}

.middleButton {
  margin-left: 0;
  margin-right: 0;
  margin-bottom: calc(var(--default-margin-value)/2);
}

@media (min-width: 1024px) {
  .header {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .header:first-child {
    width: 100%;
  }

  .middleButton {
    margin-left: auto;
    margin-right: calc(var(--default-margin-value)/2);
    margin-bottom: 0;
  }
}
</style>