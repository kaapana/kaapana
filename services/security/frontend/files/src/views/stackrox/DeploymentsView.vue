<script setup lang="ts">
import { defineComponent } from 'vue'
import Group from "@/components/Group.vue"
import GroupHeader, { type BreadCrumb } from "@/components/GroupHeader.vue"
import DeploymentList from "@/components/stackrox/DeploymentList.vue"
</script>

<template>
  <Group class="group">
    <GroupHeader title="Deployment List" :divider="true" :breadCrumbs="headerBreadCrumbs()">
    </GroupHeader>
    <DeploymentList></DeploymentList>
  </Group>
</template>

<script lang="ts">
export default defineComponent({
  methods: {
    headerBreadCrumbs(): BreadCrumb[] {
      return [
        { name: "Overview", underlined: false, routerLink: { name: "overview", params: {} } },
        { name: "Deployment List", underlined: true }
      ];
    }
  }
});
</script>

<style scoped>
.group {
  min-height: 80vh;
  display: flex;
  flex-direction: column;
}

.graph {
  flex-grow: 1;
}
</style>