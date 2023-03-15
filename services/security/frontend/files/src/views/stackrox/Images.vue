<script setup lang="ts">
import { defineComponent } from 'vue'
import Group from "@/components/Group.vue"
import GroupHeader, { type BreadCrumb } from "@/components/GroupHeader.vue"
import ImageList from "@/components/stackrox/ImageList.vue"
</script>

<template>
  <Group class="group">
    <GroupHeader title="Image List" :divider="true" :breadCrumbs="headerBreadCrumbs()">
    </GroupHeader>
    <ImageList></ImageList>
  </Group>
</template>

<script lang="ts">
export default defineComponent({
  methods: {
    headerBreadCrumbs(): BreadCrumb[] {
      return [
        { name: "Overview", underlined: false, routerLink: { name: "overview", params: {} } },
        { name: "Image List", underlined: true }
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