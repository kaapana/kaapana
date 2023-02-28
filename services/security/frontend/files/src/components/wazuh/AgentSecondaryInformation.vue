<script setup lang="ts">
import type { IAgentInformation } from '@/types/wazuh';
import { defineComponent, type PropType } from 'vue';
</script>

<template>
  <div>IP: <strong>{{ agent.ip }}</strong></div>
  <div>Name: <strong>{{ agent.name }}</strong></div>
  <div>Status: <strong>{{ agent.status }}</strong></div>
</template>

<script lang="ts">
export default defineComponent({
  props: {
    agent: {
      type: Object as PropType<IAgentInformation>,
      required: true
    }
  }
});
</script>