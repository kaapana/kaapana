<script setup lang="ts">
import { defineComponent } from 'vue'
import Group, { EGroupPadding } from "@/components/Group.vue";
import { navigateTo } from "@/router";
import ElementList, { EElementListMargin } from "@/components/ElementList.vue";
import { EDirection } from "@/types/enums";
import TextIconContainer from "@/components/icons/TextIconContainer.vue";
import { useThemeStore } from "@/stores/theme";
import { mapState } from "pinia";
import ExternalArrow from "@/components/icons/ExternalArrow.vue";
</script>

<template>
  <ElementList class="group-list" :margin=EElementListMargin.NONE :direction=EDirection.VERTICAL>
    <Group class="list-entry pointer"
      @click="navigateTo('networkgraph', { })"
      :alternativeColorScheme="false" :paddingSize=EGroupPadding.SMALL>
      <div class="group-entry">
        <div class="icon-and-text">
          <TextIconContainer containerColor="var(--color-kaapana-blue)" text="N"></TextIconContainer> Network Graph
        </div>
        <div class="arrow">►</div>
      </div>
    </Group>
    <Group class="list-entry pointer"
      @click="navigateTo('policyviolations', { })"
      :alternativeColorScheme="false" :paddingSize=EGroupPadding.SMALL>
      <div class="group-entry">
        <div class="icon-and-text">
          <TextIconContainer containerColor="var(--color-kaapana-blue)" text="§"></TextIconContainer> Policy Violations
        </div>
        <div class="arrow">►</div>
      </div>
    </Group>
    <Group class="list-entry pointer"
      @click="navigateTo('images', { })"
      :alternativeColorScheme="false" :paddingSize=EGroupPadding.SMALL>
      <div class="group-entry">
        <div class="icon-and-text">
          <TextIconContainer containerColor="var(--color-kaapana-blue)" text="I"></TextIconContainer> Images
        </div>
        <div class="arrow">►</div>
      </div>
    </Group>
    <Group class="list-entry pointer"
      @click="navigateTo('deployments', { })"
      :alternativeColorScheme="false" :paddingSize=EGroupPadding.SMALL>
      <div class="group-entry">
        <div class="icon-and-text">
          <TextIconContainer containerColor="var(--color-kaapana-blue)" text="D"></TextIconContainer> Deployments
        </div>
        <div class="arrow">►</div>
      </div>
    </Group>
    <Group class="list-entry pointer"
      @click="navigateTo('secrets', { })"
      :alternativeColorScheme="false" :paddingSize=EGroupPadding.SMALL>
      <div class="group-entry">
        <div class="icon-and-text">
          <TextIconContainer containerColor="var(--color-kaapana-blue)" text="S"></TextIconContainer> Cluster Secrets
        </div>
        <div class="arrow">►</div>
      </div>
    </Group>
    <Group v-if="complianceUrl !== null" class="list-entry pointer"
      @click="openCompliancePage"
      :alternativeColorScheme="false" :paddingSize=EGroupPadding.SMALL>
      <div class="group-entry">
        <div class="icon-and-text">
          <TextIconContainer containerColor="var(--color-kaapana-blue)" text="C"></TextIconContainer> Compliance Standards
        </div>
        <ExternalArrow class="external-arrow"></ExternalArrow>
      </div>
    </Group>
  </ElementList>
</template>

<script lang="ts">
interface OverviewData {
  complianceUrl: string | null;
}

export default defineComponent({
  data(): OverviewData {
    return {
      complianceUrl: null
    }
  },
  computed: {
    ...mapState(useThemeStore, ["useDarkMode"])
  },
  methods: {
    hoverBrightness() {
      return this.useDarkMode ? "120%" : "95%";
    },
    openCompliancePage() {
      window.open(this.complianceUrl!, '_blank')?.focus()
    },
    async getComplianceUrl() {
      const response = await fetch(window.location.origin + `/security/api/providers/stackrox/compliance-url`);
      if (response.status !== 200) {
        throw new Error("Unexpected response from backend");
      }
      const json = await response.json();

      this.complianceUrl = json["data"];
    }
  },
  async mounted() {
    await this.getComplianceUrl();
  }
});
</script>

<style scoped>
.group-list> :not(:first-child):not(:last-child) {
  border-radius: 0;
}

.pointer {
  cursor: pointer;
}

.not-allowed {
  cursor: not-allowed;
}

.list-entry:hover {
  filter: brightness(v-bind(hoverBrightness()));
}

.list-entry:first-child {
  border-bottom-right-radius: 0;
  border-bottom-left-radius: 0;
}

.list-entry:last-child {
  border-top-right-radius: 0;
  border-top-left-radius: 0;
}

.list-entry:not(:last-child) {
  border-bottom-width: 0;
}

.group-entry {
  display: flex;
  flex-direction: row;
}

.arrow, .external-arrow {
  margin-left: auto;
}

.arrow {
  transform: scale(75%, 120%);
}

.icon-and-text {
  display: flex;
  flex-direction: row;
  gap: 15px;
  align-items: center;
}
</style>