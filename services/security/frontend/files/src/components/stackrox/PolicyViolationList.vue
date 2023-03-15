
<script setup lang="ts">
import { defineComponent } from 'vue'
import Group, { EGroupPadding } from "@/components/Group.vue";
import PolicyViolation from "@/components/stackrox/PolicyViolation.vue";
import ElementList from "../ElementList.vue";
import { EDirection } from "@/types/enums";
import { EElementListMargin } from "../ElementList.vue";
import { useStackRoxStore } from '@/stores/stackrox';
import { mapWritableState } from 'pinia';
</script>

<template>
  <Group v-if="policyViolations === undefined" :alternativeColorScheme="true" :paddingSize=EGroupPadding.SMALL>Loading policy violations...</Group>
  <template v-else>
    <ElementList :direction=EDirection.VERTICAL :margin=EElementListMargin.SMALL>
      <template v-for="policyViolation of policyViolations">
        <Group :alternativeColorScheme="true">
          <PolicyViolation :policyViolation="policyViolation"></PolicyViolation>
        </Group>
      </template>
    </ElementList>
  </template>
</template>

<script lang="ts">
export default defineComponent({
  computed: {
    ...mapWritableState(useStackRoxStore, ["policyViolations"]),
  },
  methods: {
    async getPolicyViolations() {
      const response = await fetch(window.location.origin + `/security/api/providers/stackrox/policy-violations`);
      if (response.status !== 200) {
        throw new Error("Unexpected response from backend");
      }
      const json = await response.json();
      if (json["policy_violations"] === null) {
        this.policyViolations = [];
        return;
      }

      this.policyViolations = json["policy_violations"];
    }
  },
  async mounted() {
    await this.getPolicyViolations();
  }
});
</script>

<style scoped>
</style>