<script setup lang="ts">
import type { IPolicyViolation } from '@/types/stackrox';
import { defineComponent, type PropType } from 'vue'
import Extender from "@/components/Extender.vue"
import Group from "@/components/Group.vue"
import TextIconContainer from "@/components/icons/TextIconContainer.vue";
import ExternalArrow from "@/components/icons/ExternalArrow.vue"
</script>

<template>
  <div class="container">
    <div class="icon">
      <TextIconContainer class="icon-container" :containerColor="iconColor"></TextIconContainer>
    </div>
    <div class="title">
      <div><strong>{{ policyViolation.policy.severity + ' - ' + policyViolation.policy.name }}</strong> for entity '<strong>{{policyViolation.deployment.name }}</strong>'</div>
    </div>
    <div class="main">
      <div>
        <strong>Namespace:</strong> {{ policyViolation.commonEntityInfo.namespace }}
      </div>
      <div>
        <strong>Resource type:</strong> {{ policyViolation.commonEntityInfo.resourceType }}
      </div>
      <div>
        <a :href="policyViolation.externalUrl" target="_blank" rel="noopener noreferrer"><strong class="view-external-item">View externally<ExternalArrow></ExternalArrow></strong></a>
      </div>
    </div>
    <div class="additional">
      <template v-if="!hideAdditionalInfo">
        <div class="additional-text">
          <div><strong>Detected:</strong> {{ policyViolation.time }}</div>
          <div><strong>Lifecycle stage:</strong> {{ policyViolation.lifecycleStage }}</div>
        </div>
        <div><strong>Categories:</strong></div>
        <Group class="categories">
          <div v-for="category in policyViolation.policy.categories">
            • {{ category }}
          </div>
        </Group>
      </template>
    </div>
    <div class="extender">
      <Extender :reverseIcon="!hideAdditionalInfo" :onClick="toggleHide"></Extender>
    </div>
  </div>
</template>

<script lang="ts">
interface PolicyViolationData {
  hideAdditionalInfo: boolean;
}

export default defineComponent({
  props: {
    policyViolation: {
      type: Object as PropType<IPolicyViolation>,
      required: true
    }
  },
  data(): PolicyViolationData {
    return {
      hideAdditionalInfo: true
    }
  },
  computed: {
    iconColor() {
      const severity = this.policyViolation.policy.severity.toLowerCase();
      if (severity === "critical") {
        return "var(--c-color-priority-critical)";
      } else if (severity === "high") {
        return "var(--c-color-priority-high)";
      } else if (severity === "medium") {
        return "var(--c-color-priority-medium)";
      } else if (severity === "low") {
        return "var(--c-color-priority-low)";
      }
      return "var(--color-text)"
    }
  },
  methods: {
    toggleHide() {
      this.hideAdditionalInfo = !this.hideAdditionalInfo;
    }
  }
});
</script>

<style scoped>
.container {
  display: grid;
  grid-template-columns: min-content 1fr;
  grid-template-rows: min-content min-content min-content min-content min-content;
  grid-auto-rows: 1fr;
  grid-auto-flow: row;
  gap: 20px 10px;
}

.title {
  grid-area: 1 / 2 / 2 / 3;
}

.icon {
  grid-area: 1 / 1 / 2 / 2;
  align-self: center;
}

.main {
  grid-area: 2 / 1 / 4 / 3;
}
.additional {
  grid-area: 4 / 1 / 5 / 3;
}

.additional-text {
  display: flex;
  flex-direction: column;
}

.extender {
  grid-area: 5 / 1 / 6 / 3;
}

.categories {
  display: flex;
  flex-direction: column;
  overflow-wrap: break-word;
}

.view-external-item {
  display: flex;
  gap: 3px;
}

@media (min-width: 1024px) {
  .container {
    grid-template-columns: min-content 1fr 1fr;
    grid-template-rows: min-content min-content auto 25px;
  }

  .title {
    grid-area: 1 / 2 / 2 / 4;
  }

  .icon {
    grid-area: 1 / 1 / 5 / 2;
    align-self: unset;
  }

  .main {
    grid-area: 2 / 2 / 3 / 4;
  }

  .additional {
    grid-area: 3 / 2 / 4 / 4;
  }

  .additional-text {
    display: flex;
    flex-direction: row;
    gap: 20px;
  }

  .extender {
    grid-area: 4 / 2 / 5 / 4;
  }

  .icon-container {
    width: 15px;
    height: 100%;
  }
}
</style>