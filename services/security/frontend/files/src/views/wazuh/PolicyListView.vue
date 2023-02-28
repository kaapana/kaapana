<script setup lang="ts">
import { defineComponent } from 'vue'
import GroupHeader, { type BreadCrumb } from "@/components/GroupHeader.vue"
import AgentSecondaryInformation from "@/components/wazuh/AgentSecondaryInformation.vue";
import AgentSCAPolicyList from "@/components/wazuh/AgentSCAPolicyList.vue"
import Group from "@/components/Group.vue"
import { useWazuhStore } from '@/stores/wazuh';
import { mapState } from 'pinia';
</script>

<template>
  <Group>
    <GroupHeader v-if="agent !== undefined" :title="'Agent ' + agent.id" :divider="true" :breadCrumbs="headerBreadCrumbs()">
      <AgentSecondaryInformation :agent="agent"></AgentSecondaryInformation>
    </GroupHeader>
    <AgentSCAPolicyList v-if="agent !== undefined" :agent_id="agent.id"></AgentSCAPolicyList>
  </Group>
</template>

<script lang="ts">
export default defineComponent({
  computed: {
    ...mapState(useWazuhStore, {
      agentInformation: 'agentInformation', 
      agent(store) {
        return store.agentInformation?.get((this as any).$route.params.agent_id);
      }
    })
  },
  methods: {
    headerBreadCrumbs(): BreadCrumb[] {
      return [
        { name: "Overview", underlined: false, routerLink: { name: "agentlist", params: {} } },
        { name: "Policies", underlined: true }
      ];
    }
  }
});
</script>
