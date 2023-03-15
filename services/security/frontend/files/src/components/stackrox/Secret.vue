<script setup lang="ts">
import type { IPolicyViolation, ISecret } from '@/types/stackrox';
import { defineComponent, type PropType } from 'vue'
import Extender from "@/components/Extender.vue"
import Group from "@/components/Group.vue"
import ExternalArrow from "@/components/icons/ExternalArrow.vue"
</script>

<template>
  <div class="container">
    <div class="title">
      <div>Secret '<strong>{{ secret.name }}</strong>' in namespace '<strong>{{ secret.namespace }}</strong>'</div>
    </div>
    <div class="main">
      <div v-if="secret.type?.length > 0">
        <strong>Type:</strong> {{ secret.type }}
      </div>
      <div>
        <strong>Created at:</strong> {{ secret.createdAt }}
      </div>
      <div>
        <a :href="secret.externalUrl" target="_blank" rel="noopener noreferrer"><strong class="view-external-item">View externally<ExternalArrow></ExternalArrow></strong></a>
      </div>
    </div>
    <div v-if="!hideAdditionalInfo" class="additional">
      <div v-if="secret.deployments.length > 0">
        <div><strong>Used in these deployments:</strong></div>
        <Group>
          <div v-for="deployment in secret.deployments">
            • {{ deployment.name }}
          </div>
        </Group>
      </div>
      <div v-if="secret.containers.length > 0">
        <div><strong>Used in these containers:</strong></div>
        <Group>
          <div v-for="container in secret.containers">
            • {{ container.name }}
          </div>
        </Group>
      </div>
    </div>
    <div v-if="secret.deployments.length > 0 || secret.containers.length > 0" class="extender">
      <Extender :reverseIcon="!hideAdditionalInfo" :onClick="toggleHide"></Extender>
    </div>
  </div>
</template>

<script lang="ts">
interface SecretData {
  hideAdditionalInfo: boolean;
}

export default defineComponent({
  props: {
    secret: {
      type: Object as PropType<ISecret>,
      required: true
    }
  },
  data(): SecretData {
    return {
      hideAdditionalInfo: true
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
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.view-external-item {
  display: flex;
  gap: 3px;
}
</style>