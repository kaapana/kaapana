<script setup lang="ts">
import type { BreadCrumb } from '@/components/GroupHeader.vue';
import AgentSCAPolicy from '@/components/wazuh/AgentSCAPolicy.vue';
import GroupHeader from '@/components/GroupHeader.vue';
import AgentSecondaryInformation from "@/components/wazuh/AgentSecondaryInformation.vue";
import Group from '@/components/Group.vue';
import { useWazuhStore } from '@/stores/wazuh';
import { mapState } from 'pinia';
import { defineComponent } from 'vue'
</script>

<template>
  <AgentSCAPolicy v-if="policy !== undefined" :policy="policy" :agent_id="($route.params.agent_id as string)"></AgentSCAPolicy>
</template>

<script lang="ts">
export default defineComponent({
  computed: {
    ...mapState(useWazuhStore, {
      policy(store) {
        return store.policyInformation?.get((this as any).$route.params.agent_id)?.get((this as any).$route.params.policy_id);
      },
      agent(store) {
        return store.agentInformation?.get((this as any).$route.params.agent_id);
      }
    })
  }
});
</script>
