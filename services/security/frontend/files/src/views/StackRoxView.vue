<script setup lang="ts">
import Header from "@/components/Header.vue";
import Button from "@/components/Button.vue"
import { defineComponent } from 'vue'
import ExternalArrow from '@/components/icons/ExternalArrow.vue';
</script>

<template>
  <div class="header">
    <Header title="StackRox" :divider="true"></Header>
    <template v-if="stackRoxUrl !== null">
      <Button @:click="openStackRoxDashboard" class="dashboard-button"><ExternalArrow></ExternalArrow>StackRox Dashboard</Button>
    </template>
  </div>
  <main>
    <RouterView></RouterView>
  </main>
</template>

<script lang="ts">
interface IViewData {
  stackRoxUrl: string | null;
}

export default defineComponent({
  data(): IViewData {
    return {
      stackRoxUrl: null
    };
  },
  methods: {
    async getStackRoxUrl() {
      const response = await fetch(window.location.origin + "/security/api/providers/stackrox/url");
      if (response.status !== 200) {
        throw new Error("Unexpected response from backend");
      }
      const json = await response.json();
      this.stackRoxUrl = json["data"];
    },
    openStackRoxDashboard() {
      if (this.stackRoxUrl) {
        window.open(this.stackRoxUrl, "_blank")?.focus();
      }
    }
  },
  async mounted() {
    const wazuh_url_promise = this.getStackRoxUrl();
    await Promise.all([wazuh_url_promise]);
  }
});
</script>

<style scoped>
.header {
  display: flex;
  width: 100%;
  flex-direction: column;
  margin-bottom: var(--default-margin-value);
}

.dashboard-button {
  margin-left: 0;
  margin-right: 0;
  margin-bottom: calc(var(--default-margin-value)/2);
}

@media (min-width: 1024px) {
  .header {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .header:first-child {
    width: 100%;
  }

  .dashboard-button {
    margin-left: auto;
    margin-bottom: 0;
  }
}
</style>