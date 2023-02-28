
<script setup lang="ts">
import type { IAgentSCAPolicy } from "@/types/wazuh";
import { defineComponent } from 'vue'
import Group, { EGroupPadding } from "@/components/Group.vue";
import { navigateTo } from "@/router";
import ElementList from "../ElementList.vue";
import { EDirection } from "@/types/enums";
import { EElementListMargin } from "../ElementList.vue";
import { useWazuhStore, type PolicyInformationMap } from '@/stores/wazuh';
import { mapState, mapWritableState } from 'pinia';
</script>

<template>
  <Group v-if="scaPolicyList === undefined" :alternativeColorScheme="true" :paddingSize=EGroupPadding.SMALL>Loading policies...</Group>
  <div v-else-if="scaPolicyList.size === 0">
    {{ `No policies found, either restart agent ${agent_id} manually by executing 'sudo systemctl disable wazuh-agent && sudo systemctl enable wazuh-agent && sudo systemctl start wazuh-agent' on the system it is installed on or wait until the security configuration assessment is triggered again by Wazuh (this can take up to 30 minutes).` }}
  </div>
  <template v-else>
    <ElementList :direction=EDirection.VERTICAL :margin=EElementListMargin.NONE>
      <template v-for="[_, policy] of scaPolicyList">
        <Group class="list-entry" @click="navigateTo('policy', { agent_id: agent_id, policy_id: policy.id })" :alternativeColorScheme="true" :paddingSize=EGroupPadding.SMALL>
          <div class="group-entry">
            <div>{{ policy.name }}</div>
            <div class="arrow">►</div>
          </div>
        </Group>
      </template>
    </ElementList>
  </template>
</template>

<script lang="ts">
export default defineComponent({
  props: {
    agent_id: {
      type: String,
      required: true
    }
  },
  computed: {
    ...mapWritableState(useWazuhStore, ["policyInformation"]),
    ...mapState(useWazuhStore, {
      scaPolicyList(store) {
        return store.policyInformation?.get((this as any).agent_id);
      }
    })
  },
  methods: {
    async getSCAPolicyList() {
      if (this.policyInformation === null) {
        this.policyInformation = new Map();
      }

      const response = await fetch(window.location.origin + `/security/api/providers/wazuh/agents/${this.agent_id}/sca`);
      if (response.status !== 200) {
        throw new Error("Unexpected response from backend");
      }
      const json = await response.json();
      if (json["sca_policies"] === null) {
        this.policyInformation.set(this.agent_id, new Map());
        return;
      }

      const agentPolicyInformation = json["sca_policies"].reduce((acc: PolicyInformationMap, policy: IAgentSCAPolicy) => {
        acc.set(policy.id, policy);
        return acc;
      }, new Map());

      this.policyInformation.set(this.agent_id, agentPolicyInformation);
    }
  },
  async mounted() {
    await this.getSCAPolicyList();
  }
});
</script>

<style scoped>
.list-entry {
  cursor: pointer;
}

.group-entry {
  display: flex;
  flex-direction: row;
}

.arrow {
  margin-left: auto;
  transform: scale(75%, 120%);
}
</style>