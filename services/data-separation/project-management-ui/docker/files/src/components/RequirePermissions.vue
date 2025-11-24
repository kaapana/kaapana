<script setup lang="ts">
import { usePermissions } from "@/permissions/usePermissions";

defineProps<{
  projectId: string;
  permission: string;
}>();

const { can } = usePermissions();
</script>



<template>
  <slot v-if="can(projectId, permission)" />
</template>
