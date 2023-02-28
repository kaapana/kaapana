<script setup lang="ts">
import type { IAgentSCAPolicy, IAgentSCAPolicyCheck } from "@/types/wazuh";
import { defineComponent } from 'vue'
import type { PropType } from 'vue';
import Group, { EGroupPadding } from "@/components/Group.vue";
import GroupHeader, { type BreadCrumb } from "@/components/GroupHeader.vue";
import AgentSCAPolicyCheckList from "./AgentSCAPolicyCheckList.vue";
import ElementList, { EElementListMargin } from "../ElementList.vue";
import { EDirection } from "@/types/enums";
</script>

<template>
  <Group :paddingSize=EGroupPadding.NORMAL>
    <GroupHeader :title="'Policy ' + policy.id" :divider="true" :breadCrumbs="headerBreadCrumbs()">
      <div>Policy name: <strong>{{ policy.name }}</strong></div>
      <div class="flex-row-container">
        <div class="passed">✓</div><div>Passed checks: <strong>{{ policy.passed }}</strong></div>
      </div>
      <div class="flex-row-container">
        <div class="failed">✗</div><div>Failed checks: <strong>{{ policy.failed }}</strong></div>
      </div>
      <div class="flex-row-container">
        <div class="unapplicable">⊘</div><div>Unapplicable checks: <strong>{{ policy.unapplicable }}</strong></div>
      </div>
    </GroupHeader>

    <div v-if="scaPolicyChecks === null">Loading policy checks...</div>
    <div v-else-if="scaPolicyChecks.length === 0">No policy checks found</div>
    <template v-else>
      <ElementList :margin=EElementListMargin.SMALL :direction=EDirection.VERTICAL>
        <AgentSCAPolicyCheckList :checkList="failedChecks!"></AgentSCAPolicyCheckList>
        <AgentSCAPolicyCheckList :checkList="passedChecks!"></AgentSCAPolicyCheckList>
        <AgentSCAPolicyCheckList :checkList="unapplicableChecks!"></AgentSCAPolicyCheckList>
      </ElementList>
    </template>
  </Group>
</template>

<script lang="ts">
interface AgentSCAPolicyData {
  scaPolicyChecks: IAgentSCAPolicyCheck[] | null
}

export default defineComponent({
  props: {
    agent_id: {
      type: String,
      required: true
    },
    policy: {
      type: Object as PropType<IAgentSCAPolicy>,
      required: true
    }
  },
  data(): AgentSCAPolicyData {
    return {
      scaPolicyChecks: null
    };
  },
  computed: {
    failedChecks() {
      return this.scaPolicyChecks?.filter(check => check.result === "failed");
    },
    passedChecks() {
      return this.scaPolicyChecks?.filter(check => check.result === "passed");
    },
    unapplicableChecks() {
      return this.scaPolicyChecks?.filter(check => check.result !== "failed" && check.result !== "passed");
    }
  },
  methods: {
    async getSCAPolicyChecks() {
      const response = await fetch(window.location.origin + `/security/api/providers/wazuh/agents/${this.agent_id}/sca/${this.policy.id}`);
      if (response.status !== 200) {
        throw new Error("Unexpected response from backend");
      }
      const json = await response.json();
      if (json["sca_policy_checks"] === null) {
        this.scaPolicyChecks = [];
        return;
      }
      this.scaPolicyChecks = json["sca_policy_checks"];
    },
    headerBreadCrumbs(): BreadCrumb[] {
      return [
        { name: "Overview", underlined: false, routerLink: { name: "agentlist", params: {} } },
        { name: `Agent ${this.$route.params.agent_id} policies`, underlined: false, routerLink:
          { name: "policylist", params: { agent_id: this.$route.params.agent_id } }
        },
        { name: `Policy '${this.$route.params.policy_id}'`, underlined: true },
      ];
    }
  },
  async mounted() {
    await this.getSCAPolicyChecks();
  }
});
</script>

<style scoped>
.flex-row-container {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.passed {
  color: var(--color-success-background);
  font-size: 150%;
  transform: scale(1.2);
  /* checkmark is a little smaller than cross */
}

.failed {
  color: var(--color-warning-background);
  font-size: 150%;
}

.unapplicable {
  font-size: 150%;
}
</style>