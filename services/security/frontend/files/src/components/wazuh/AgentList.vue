<script setup lang="ts">
import Group from "@/components/Group.vue";
import { defineComponent } from 'vue'
import type { PropType } from 'vue';
import AgentOverview from "@/components/wazuh/AgentOverview.vue"
import ElementList, { EElementListMargin } from "../ElementList.vue";
import { EDirection } from "@/types/enums";
import type { AgentInformationMap } from "@/stores/wazuh";
</script>

<template>
  <ElementList :margin=EElementListMargin.NORMAL :direction=EDirection.VERTICAL>
    <template v-for="[_, agent] of agentInformation">
      <Group>
        <AgentOverview :agent="agent"></AgentOverview>
      </Group>
    </template>
  </ElementList>
</template>

<script lang="ts">
export default defineComponent({
  props: {
    agentInformation: {
      type: Object as PropType<AgentInformationMap>,
      required: true
    }
  }
});
</script>