
<script setup lang="ts">
import { defineComponent } from 'vue'
import Group, { EGroupPadding } from "@/components/Group.vue";
import Secret from "@/components/stackrox/Secret.vue";
import ElementList from "../ElementList.vue";
import { EDirection } from "@/types/enums";
import { EElementListMargin } from "../ElementList.vue";
import { useStackRoxStore } from '@/stores/stackrox';
import { mapWritableState } from 'pinia';
</script>

<template>
  <Group v-if="secrets === undefined" :alternativeColorScheme="true" :paddingSize=EGroupPadding.SMALL>Loading secrets...</Group>
  <template v-else>
    <ElementList :direction=EDirection.VERTICAL :margin=EElementListMargin.SMALL>
      <template v-for="secret of secrets">
        <Group :alternativeColorScheme="true">
          <Secret :secret="secret"></Secret>
        </Group>
      </template>
    </ElementList>
  </template>
</template>

<script lang="ts">
export default defineComponent({
  computed: {
    ...mapWritableState(useStackRoxStore, ["secrets"]),
  },
  methods: {
    async getSecrets() {
      const response = await fetch(window.location.origin + `/security/api/providers/stackrox/secrets`);
      if (response.status !== 200) {
        throw new Error("Unexpected response from backend");
      }
      const json = await response.json();
      if (json["secrets"] === null) {
        this.secrets = [];
        return;
      }

      this.secrets = json["secrets"];
    }
  },
  async mounted() {
    await this.getSecrets();
  }
});
</script>

<style scoped>
</style>