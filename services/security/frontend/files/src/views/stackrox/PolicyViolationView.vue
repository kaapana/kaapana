<script setup lang="ts">
import { defineComponent } from 'vue'
import Group from "@/components/Group.vue"
import GroupHeader, { type BreadCrumb } from "@/components/GroupHeader.vue"
import PolicyViolationList from "@/components/stackrox/PolicyViolationList.vue"
</script>

<template>
  <Group>
    <GroupHeader title="Policy Violations" :divider="true" :breadCrumbs="headerBreadCrumbs()">
    </GroupHeader>
    <PolicyViolationList></PolicyViolationList>
  </Group>
</template>

<script lang="ts">
export default defineComponent({
  methods: {
    headerBreadCrumbs(): BreadCrumb[] {
      return [
        { name: "Overview", underlined: false, routerLink: { name: "overview", params: {} } },
        { name: "Policy Violations", underlined: true }
      ];
    }
  }
});
</script>

<style scoped>

</style>