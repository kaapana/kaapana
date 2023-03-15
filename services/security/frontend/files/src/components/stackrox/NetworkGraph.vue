<script setup lang="ts">
import { defineComponent } from 'vue'
import ExternalArrow from '@/components/icons/ExternalArrow.vue';
</script>

<template>
  <div class="container">
    <div v-if="url === null">Loading ...</div>
    <template v-else>
      <a :href="url" target="_blank" rel="noopener noreferrer"><strong class="view-external-item">View externally<ExternalArrow class="external-arrow"></ExternalArrow></strong></a>
      <iframe class="network-graph" :src="url"></iframe>
    </template>
  </div>
</template>

<script lang="ts">
interface NetworkGraphData {
  url: string | null;
}
export default defineComponent({
    data() {
        return {
            url: null
        };
    },
    methods: {
        async getNetworkGraphUrl() {
            const response = await fetch(window.location.origin + `/security/api/providers/stackrox/networkgraph-url`);
            if (response.status !== 200) {
                throw new Error("Unexpected response from backend");
            }
            const json = await response.json();
            this.url = json["networkgraph_url"];
        }
    },
    async mounted() {
        await this.getNetworkGraphUrl();
    }
});
</script>

<style scoped>
.container {
  display:flex;
  flex-direction: column;
  gap: 10px;
}

.network-graph {
  width: 100%;
  height: 100%;
  border: none;
  flex-grow: 1;
}

.view-external-item {
  display: flex;
  gap: 3px;
}
</style>