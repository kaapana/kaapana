<script setup lang="ts">
import { defineComponent } from 'vue';
import type { IAgentSCAPolicyCheck } from "@/types/wazuh";
import type { PropType } from 'vue';
import Group from "@/components/Group.vue";
import ElementList, { EElementListMargin } from "@/components/ElementList.vue";
import { EDirection } from "@/types/enums";
import AgentSCAPolicyCheck from "@/components/wazuh/AgentSCAPolicyCheck.vue"
</script>

<template>
  <ElementList class="group-list" :margin=EElementListMargin.NONE :direction=EDirection.VERTICAL>
    <template v-for="[checkId, policyCheck] of checkList.entries()">
      <Group :alternative-color-scheme="true" class="list-entry" @click="toggleHidden(checkId)">
        <AgentSCAPolicyCheck :hideAdditionalInfo="isHidden(checkId)" :policyCheck="policyCheck"></AgentSCAPolicyCheck>
      </Group>
    </template>
  </ElementList>
</template>

<script lang="ts">
interface AgentSCAPolicyCheckListData {
  checkHiddenStatus: Map<number, boolean>;
}

export default defineComponent({
  props: {
    checkList: {
      type: Object as PropType<IAgentSCAPolicyCheck[]>,
      required: true
    }
  },
  data(): AgentSCAPolicyCheckListData {
    return {
      checkHiddenStatus: new Map()
    };
  },
  methods: {
    toggleHidden(checkId: number) {
      this.checkHiddenStatus.set(checkId, !this.isHidden(checkId));
    },
    isHidden(checkId: number) {
      if (!this.checkHiddenStatus.has(checkId)) { 
        this.checkHiddenStatus.set(checkId, true);
      }
      return this.checkHiddenStatus.get(checkId)!;
    }
  }
});
</script>

<style scoped>
.group-list {
  width: 100%
}

.group-list> :not(:first-child):not(:last-child) {
  border-radius: 0;
}

.list-entry {
  cursor: pointer;
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
</style>