<script setup lang="ts">
import type { IDeployment } from '@/types/stackrox';
import { defineComponent, type PropType } from 'vue'
import TextIconContainer from "@/components/icons/TextIconContainer.vue";
import ExternalArrow from "@/components/icons/ExternalArrow.vue"
</script>

<template>
  <div class="container">
    <div class="icon">
      <TextIconContainer class="icon-container" :containerColor="iconColor"></TextIconContainer>
    </div>
    <div class="title">
      <strong>{{ deployment.name }}</strong>
    </div>
    <div class="main">
      <div>
        <strong>Risk priority:</strong> {{ deployment.priority }}
      </div>
      <div>
        <strong>Risk score:</strong> {{ deployment.riskScore }}
      </div>
      <div>
        <strong>Namespace:</strong> {{ deployment.namespace }}
      </div>
      <div>
        <a :href="deployment.externalUrl" target="_blank" rel="noopener noreferrer"><strong class="view-external-item">View externally<ExternalArrow></ExternalArrow></strong></a>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
export default defineComponent({
  props: {
    deployment: {
      type: Object as PropType<IDeployment>,
      required: true
    }
  },
  computed: {
    iconColor() {
      const riskScore = this.deployment.riskScore;
      if (riskScore >= 8) {
        return "var(--c-color-priority-critical)";
      } else if (riskScore >= 5) {
        return "var(--c-color-priority-high)";
      } else if (riskScore >= 3) {
        return "var(--c-color-priority-medium)";
      } else {
        return "var(--c-color-priority-low)";
      }
    }
  }
});
</script>

<style scoped>
.container {
  display: grid;
  grid-template-columns: min-content 1fr;
  grid-template-rows: min-content min-content;
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
  grid-area: 2 / 1 / 3 / 3;
}

.view-external-item {
  display: flex;
  gap: 3px;
}

@media (min-width: 1024px) {
  .container {
    grid-template-columns: min-content 1fr;
    grid-template-rows: min-content min-content;
  }

  .title {
    grid-area: 1 / 2 / 2 / 3;
  }

  .icon {
    grid-area: 1 / 1 / 3 / 2;
    align-self: unset;
  }

  .main {
    grid-area: 2 / 2 / 3 / 3;
  }

  .icon-container {
    width: 15px;
    height: 100%;
  }
}
</style>