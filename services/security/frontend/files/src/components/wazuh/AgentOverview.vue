<script setup lang="ts">
import { type IAgentInformation, agentStatusGate } from "@/types/wazuh";
import { defineComponent } from 'vue'
import type { PropType } from 'vue';
import GroupHeader from "@/components/GroupHeader.vue";
import AgentSecondaryInformation from "@/components/wazuh/AgentSecondaryInformation.vue";
import Group, { EGroupPadding } from "@/components/Group.vue";
import { navigateTo } from "@/router";
import ElementList, { EElementListMargin } from "@/components/ElementList.vue";
import { EDirection } from "@/types/enums";
import TextIconContainer from "../icons/TextIconContainer.vue";
</script>

<template>
  <GroupHeader :title="'Agent ' + agent.id" :divider="true">
    <AgentSecondaryInformation :agent="agent"></AgentSecondaryInformation>
  </GroupHeader>
  <ElementList class="group-list" :margin=EElementListMargin.NONE :direction=EDirection.VERTICAL>
    <Group :class="listEntryCssClasses(agent)" @click="agentStatusGate(agent, () => navigateTo('vulnerabilitylist', {agent_id: agent.id}))" :alternativeColorScheme="true" :paddingSize=EGroupPadding.SMALL>
      <div class="group-entry">
        <div class="icon-and-text">
          <TextIconContainer containerColor="var(--color-kaapana-blue)" text="!!"></TextIconContainer> Vulnerabilities
        </div>
        <div class="arrow">►</div>
      </div>
    </Group>
    <Group :class="listEntryCssClasses(agent)" @click="agentStatusGate(agent, () => navigateTo('policylist', {agent_id: agent.id}))" :alternativeColorScheme="true" :paddingSize=EGroupPadding.SMALL>
      <div class="group-entry">
        <div class="icon-and-text">
          <TextIconContainer containerColor="var(--color-kaapana-blue)" text="§"></TextIconContainer> Policies
        </div>
        <div class="arrow">►</div>
      </div>
    </Group>
    <Group :class="listEntryCssClasses(agent)" @click="agentStatusGate(agent, () => navigateTo('fileintegritylist', {agent_id: agent.id}))" :alternativeColorScheme="true" :paddingSize=EGroupPadding.SMALL>
      <div class="group-entry">
        <div class="icon-and-text">
          <TextIconContainer containerColor="var(--color-kaapana-blue)" text="[]"></TextIconContainer> File Integrity Monitoring
        </div>
        <div class="arrow">►</div>
      </div>
    </Group>
  </ElementList>
</template>

<script lang="ts">
export default defineComponent({
    props: {
        agent: {
            type: Object as PropType<IAgentInformation>,
            required: true
        }
    },
    methods: {
        listEntryCssClasses(agent: IAgentInformation) {
            const classes: string[] = [];
            classes.push("list-entry");
            if (agent.status === "active") {
                classes.push("pointer");
            }
            else {
                classes.push("not-allowed");
            }
            return classes.join(" ");
        }
    }
});
</script>

<style scoped>
.group-list > :not(:first-child):not(:last-child)  {
  border-radius: 0;
}

.pointer {
  cursor: pointer;
}

.not-allowed {
  cursor: not-allowed;
}

.list-entry:first-child {
  border-bottom-right-radius: 0;
  border-bottom-left-radius: 0;
}

.list-entry:last-child {
  border-top-right-radius: 0;
  border-top-left-radius: 0;
}

.list-entry:not(:last-child) {
  border-bottom-width: 0;
}

.group-entry {
  display: flex;
  flex-direction: row;
}

.arrow {
  margin-left: auto;
  transform: scale(75%, 120%);
}

.icon-and-text {
  display: flex;
  flex-direction: row;
  gap: 15px;
  align-items: center;
}
</style>