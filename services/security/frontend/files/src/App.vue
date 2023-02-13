<script setup lang="ts">
import { defineComponent } from 'vue'
import { RouterView } from "vue-router";
import { DARK_MODE_ACTIVE, DARK_MODE_NOT_ACTIVE, QUERY_DARK_MODE } from "@/stores/messages.types";
import { useThemeStore, updateThemeCss } from "@/stores/theme";
import { mapWritableState } from 'pinia';
import ErrorBoundary from "@/components/ErrorBoundary.vue"
</script>

<template>
  <ErrorBoundary>
    <RouterView />
  </ErrorBoundary>
</template>

<script lang="ts">
export default defineComponent({
  data() {
    return {
      wazuhAgentAvailable: null
    };
  },
  computed: {
    ...mapWritableState(useThemeStore, ["useDarkMode"])
  },
  methods: {
    async checkWazuhAgents() {
      const response = await fetch(window.location.origin + "/security/api/extension/wazuh/agent-installed");
      const json = await response.json();
      this.wazuhAgentAvailable = json["agent_installed"];
    },
    updateCss () {
      updateThemeCss(document, this.useDarkMode);
    },
    receiveMessage(event: MessageEvent) {
      console.log(event);

      // only process our own messages
      if (event.origin !== window.location.origin || !("message" in event.data)) {
        return;
      }
      if (event.data.message === DARK_MODE_ACTIVE) {
        this.useDarkMode = true;
        this.updateCss();
      } else if (event.data.message === DARK_MODE_NOT_ACTIVE) {
        this.useDarkMode = false;
        this.updateCss();
      }
    }
  },
  created() {
    window.addEventListener("message", this.receiveMessage);

    if (window.parent) {
      window.parent.postMessage({message: QUERY_DARK_MODE}, "*");
    }
  },
  beforeDestroy() {
    window.removeEventListener("message", this.receiveMessage);
  }
});
</script>
