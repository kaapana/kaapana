<template>
  <iframe
    id="ifrm"
    v-bind:src="api_base_path"
    width="100%"
    height="100%"
  ></iframe>
</template>

<script lang="ts">
import { mapState } from "pinia";
import { useAppStore } from "@/store/app";

export default {
  computed: {
    ...mapState(useAppStore, ["api_base_path"]),
  },
};
</script>
