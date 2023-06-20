<script setup lang="ts">
import type { IAgentFileIntegrityAlert } from '@/types/wazuh';
import { defineComponent, type PropType } from 'vue';
import Group from "@/components/Group.vue"
</script>

<template>
  <div class="container">
    <div>
      <strong>Affected path:</strong> {{ fileIntegrityAlert.path }}
    </div>
    <div class="rule">
      <div>
        <strong>Rule level:</strong> {{ fileIntegrityAlert.rule.level }}
      </div>
      <div>
        <strong>Rule description:</strong> {{ fileIntegrityAlert.rule.description }}
      </div>
    </div>
    <div>
      <strong>Full log:</strong>
      <Group class="log-entries">
        <template v-for="log_entry of fileIntegrityAlert.full_log.split(/(?=[A-Z])/)">
          <div>{{ log_entry }}</div>
        </template>
      </Group>
    </div>
  </div>
</template>

<script lang="ts">
export default defineComponent({
  props: {
    fileIntegrityAlert: {
      type: Object as PropType<IAgentFileIntegrityAlert>,
      required: true
    }
  }
});
</script>

<style scoped>
.container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rule {
  display: flex;
  flex-direction: row;
  gap: 20px;
}

.log-entries {
  display: flex;
  flex-direction: column;
}
</style>