<script setup lang="ts">
import { defineComponent } from 'vue'
import { RouterView } from "vue-router";
import { DARK_MODE_ACTIVE, DARK_MODE_NOT_ACTIVE, QUERY_DARK_MODE } from "@/stores/messages.types";
import { useThemeStore, updateThemeCss } from "@/stores/theme";
import { mapWritableState } from 'pinia';
import ErrorBoundary from "@/components/ErrorBoundary.vue"
import Notifications from "@/components/Notifications.vue"
</script>

<template>
  <ErrorBoundary>
    <RouterView class="router"></RouterView>
    <Notifications :notifications="notifications"></Notifications>
  </ErrorBoundary>
</template>

<script lang="ts">
interface AppData {
  notification_interval: number | null;
  notifications: any[];
}

export default defineComponent({
  data(): AppData {
    return {
      notification_interval: null,
      notifications: []
    }
  },
  computed: {
    ...mapWritableState(useThemeStore, ["useDarkMode"])
  },
  methods: {
    updateCss () {
      updateThemeCss(document, this.useDarkMode);
    },
    receiveMessage(event: MessageEvent) {
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
    },
    hoverBrightness() {
      return this.useDarkMode ? "120%" : "95%";
    }
  },
  created() {
    window.addEventListener("message", this.receiveMessage);

    if (window.parent) {
      window.parent.postMessage({message: QUERY_DARK_MODE}, "*");
    }

    this.notification_interval = window.setInterval(async () => {
      const response = await fetch(`${window.location.origin}/security/api/notifications`);
      if (response.status !== 200) {
        this.notifications = ["Could not get notifications from backend."];
      }
      const json = await response.json();
      if (json["notifications"] === null) {
        this.notifications = [];
        return;
      }
      this.notifications = json["notifications"];
      this.notifications.push({title: "test test test test test test test test", description: "desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc desc", link: "no link"});
    }, 5000);
  },
  beforeDestroy() {
    window.removeEventListener("message", this.receiveMessage);
    if (this.notification_interval) {
      window.clearInterval(this.notification_interval);
    }
  }
});
</script>

<style>

@media (hover: hover) {
  a {
    color: var(--color-text);
  }

  a:hover {
    filter: brightness(v-bind(hoverBrightness()));
  }
}
</style>
