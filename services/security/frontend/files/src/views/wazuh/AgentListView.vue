<script setup lang="ts">
import { defineComponent } from 'vue';
import { useWazuhStore } from "@/stores/wazuh";
import { mapState } from "pinia";
import AgentList from "@/components/wazuh/AgentList.vue"
</script>

<template>
  <AgentList :agentInformation="agentInformation!"></AgentList>
</template>

<script lang="ts">
export default defineComponent({
  computed: {
    ...mapState(useWazuhStore, ["agentInformation"]) // we can assume that the information is available here, as WazuhView does not render this View if it is not
  },
});
</script>