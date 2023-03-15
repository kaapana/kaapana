<script setup lang="ts">
import { defineComponent } from 'vue'
import Group from "@/components/Group.vue"
import GroupHeader, { type BreadCrumb } from "@/components/GroupHeader.vue"
import NetworkGraph from "@/components/stackrox/NetworkGraph.vue"
</script>

<template>
  <Group class="group">
    <GroupHeader title="Network Graph" :divider="true" :breadCrumbs="headerBreadCrumbs()">
    </GroupHeader>
    <NetworkGraph class="graph"></NetworkGraph>
  </Group>
</template>

<script lang="ts">
export default defineComponent({
  methods: {
    headerBreadCrumbs(): BreadCrumb[] {
      return [
        { name: "Overview", underlined: false, routerLink: { name: "overview", params: {} } },
        { name: "Network Graph", underlined: true }
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