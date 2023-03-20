
<script setup lang="ts">
import { defineComponent } from 'vue'
import Group, { EGroupPadding } from "@/components/Group.vue";
import Deployment from "@/components/stackrox/Deployment.vue";
import ElementList from "../ElementList.vue";
import { EDirection } from "@/types/enums";
import { EElementListMargin } from "../ElementList.vue";
import { useStackRoxStore } from '@/stores/stackrox';
import { mapWritableState } from 'pinia';
</script>

<template>
  <Group v-if="deployments === undefined" :alternativeColorScheme="true" :paddingSize=EGroupPadding.SMALL>Loading deployments...</Group>
  <template v-else>
    <ElementList :direction=EDirection.VERTICAL :margin=EElementListMargin.SMALL>
      <template v-for="deployment of deployments">
        <Group :alternativeColorScheme="true">
          <Deployment :deployment="deployment"></Deployment>
        </Group>
      </template>
    </ElementList>
  </template>
</template>

<script lang="ts">
export default defineComponent({
  computed: {
    ...mapWritableState(useStackRoxStore, ["deployments"]),
  },
  methods: {
    async getDeployments() {
      const response = await fetch(window.location.origin + `/security/api/providers/stackrox/deployments`);
      if (response.status !== 200) {
        throw new Error("Unexpected response from backend");
      }
      const json = await response.json();
      if (json["data"] === null) {
        this.deployments = [];
        return;
      }

      this.deployments = json["data"];
    }
  },
  async mounted() {
    await this.getDeployments();
  }
});
</script>

<style scoped>
</style>