
<script setup lang="ts">
import { defineComponent } from 'vue'
import Group, { EGroupPadding } from "@/components/Group.vue";
import Image from "@/components/stackrox/Image.vue";
import ElementList from "../ElementList.vue";
import { EDirection } from "@/types/enums";
import { EElementListMargin } from "../ElementList.vue";
import { useStackRoxStore } from '@/stores/stackrox';
import { mapWritableState } from 'pinia';
</script>

<template>
  <Group v-if="images === undefined" :alternativeColorScheme="true" :paddingSize=EGroupPadding.SMALL>Loading images...</Group>
  <template v-else>
    <ElementList :direction=EDirection.VERTICAL :margin=EElementListMargin.SMALL>
      <template v-for="image of images">
        <Group :alternativeColorScheme="true">
          <Image :image="image"></Image>
        </Group>
      </template>
    </ElementList>
  </template>
</template>

<script lang="ts">
export default defineComponent({
  computed: {
    ...mapWritableState(useStackRoxStore, ["images"]),
  },
  methods: {
    async getImages() {
      const response = await fetch(window.location.origin + `/security/api/providers/stackrox/images`);
      if (response.status !== 200) {
        throw new Error("Unexpected response from backend");
      }
      const json = await response.json();
      if (json["data"] === null) {
        this.images = [];
        return;
      }

      this.images = json["data"];
    }
  },
  async mounted() {
    await this.getImages();
  }
});
</script>

<style scoped>
</style>