<script setup lang="ts">
import type { IAgentSCAPolicyCheck } from '@/types/wazuh';
import { defineComponent, type PropType } from 'vue';
import Extender from "@/components/Extender.vue"
</script>

<template>
  <div class="flex-row-container">
    <div v-if="checkFailed" class="failed">✗</div>
    <div v-else-if="checkPassed" class="passed">✓</div>
    <div v-else class="unapplicable">⊘</div>
    <div class="policy-check-title">{{ policyCheck.title }}</div>
  </div>
  <div :class="!hideAdditionalInfo ? 'additional-content' : ''">
    <div v-if="policyCheck.remediation && checkFailed"><strong>Remediation:</strong> {{ policyCheck.remediation }}</div>
    <Extender v-if="hideAdditionalInfo" class="extender"></Extender>
    <template v-else>
      <div><strong>Description:</strong> {{ policyCheck.description }}</div>
      <div><strong>Rationale:</strong> {{ policyCheck.rationale }}</div>
      <div v-if="policyCheck.references"><strong>References:</strong> {{ policyCheck.references }}</div>
      <div v-if="policyCheck.file"><strong>File:</strong> {{ policyCheck.file }}</div>
      <div v-if="policyCheck.directory"><strong>Directory:</strong> {{ policyCheck.directory }}</div>
      <div v-if="policyCheck.command"><strong>Command:</strong> {{ policyCheck.command }}</div>
    </template>
  </div>
</template>

<script lang="ts">
export default defineComponent({
  props: {
    hideAdditionalInfo: {
      type: Boolean,
      required: true
    },
    policyCheck: {
      type: Object as PropType<IAgentSCAPolicyCheck>,
      required: true
    }
  },
  computed: {
    checkFailed() {
      return this.policyCheck.result === "failed";
    },
    checkPassed() {
      return this.policyCheck.result === "passed";
    }
  }
});
</script>

<style scoped>
.flex-row-container {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
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

.policy-check-title {
  font-weight: bold;
}

.additional-content, .extender {
  margin-top: calc(var(--default-margin-value) / 2);
}

</style>