
<script setup lang="ts">
import type { IAgentFileIntegrityAlert } from "@/types/wazuh";
import { defineComponent } from 'vue'
import Group, { EGroupPadding } from "@/components/Group.vue";
import AgentFileIntegrity from "@/components/wazuh/AgentFileIntegrity.vue";
import ElementList from "../ElementList.vue";
import { EDirection } from "@/types/enums";
import { EElementListMargin } from "../ElementList.vue";
import { useWazuhStore, type FileIntegrityInformationMap } from '@/stores/wazuh';
import { mapState, mapWritableState } from 'pinia';
</script>

<template>
  <Group v-if="fileIntegrityAlertList === undefined" :alternativeColorScheme="true" :paddingSize=EGroupPadding.SMALL>Loading file integrity alerts...</Group>
  <div v-else-if="fileIntegrityAlertList.size === 0">No file integrity alerts found.</div>
  <template v-else>
    <ElementList :direction=EDirection.VERTICAL :margin=EElementListMargin.SMALL>
      <template v-for="[_, fileIntegrityAlert] of fileIntegrityAlertList">
        <Group :alternativeColorScheme="true">
          <AgentFileIntegrity :fileIntegrityAlert="fileIntegrityAlert"></AgentFileIntegrity>
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
    ...mapWritableState(useWazuhStore, ["fileIntegrityInformation"]),
    ...mapState(useWazuhStore, {
      fileIntegrityAlertList(store) {
        return store.fileIntegrityInformation?.get((this as any).agent_id);
      }
    })
  },
  methods: {
    async getFileIntegrityInformation() {
      if (this.fileIntegrityInformation === null) {
        this.fileIntegrityInformation = new Map();
      }

      const response = await fetch(window.location.origin + `/security/api/providers/wazuh/agents/${this.agent_id}/file-integrity-alerts`);
      if (response.status !== 200) {
        throw new Error("Unexpected response from backend");
      }
      const json = await response.json();
      if (json["file_integrity_alerts"] === null) {
        this.fileIntegrityInformation.set(this.agent_id, new Map());
        return;
      }

      const agentFileIntegrityInformation = json["file_integrity_alerts"].reduce((acc: FileIntegrityInformationMap, fileIntegrityAlert: IAgentFileIntegrityAlert) => {
        acc.set(fileIntegrityAlert.id, fileIntegrityAlert);
        return acc;
      }, new Map());

      this.fileIntegrityInformation.set(this.agent_id, agentFileIntegrityInformation);
    }
  },
  async mounted() {
    await this.getFileIntegrityInformation();
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