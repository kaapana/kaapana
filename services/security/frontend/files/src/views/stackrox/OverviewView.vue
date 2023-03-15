<script setup lang="ts">
import { defineComponent } from 'vue';
import GroupHeader from "@/components/GroupHeader.vue";
import Overview from "@/components/stackrox/Overview.vue"
</script>

<template>
  <GroupHeader title="Overview" :divider="false">
  </GroupHeader>
  <Overview></Overview>
</template>

<script lang="ts">
export default defineComponent({
});
</script>