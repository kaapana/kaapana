<template>
  <!-- <v-expansion-panels v-if="schemas">
    <v-expansion-panel v-for="version in versions" :key="version">
      <v-expansion-panel-title>Version {{ version }}</v-expansion-panel-title>
      <v-expansion-panel-text>
        <v-textarea auto-grow row-height="30" rows="40" variant="outlined" :value="JSON.stringify(schemas[version], null, 2)"></v-textarea>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels> -->
  <v-card v-if="schemas">
    <v-tabs v-model="tab">
      <v-tab :value="version" v-for="version in versions">{{ version }} </v-tab>
    </v-tabs>
    <v-card-text>
      <v-window v-model="tab">
        <v-window-item v-for="version in versions" :value="version">
          <router-link :to="`/urn/${urn}:${version}`">{{
            `${urn}:${version}`
          }}</router-link>
          <v-textarea
            rows="40"
            variant="outlined"
            :value="JSON.stringify(schemas[version], null, 2)"
          ></v-textarea>
        </v-window-item>
      </v-window>
    </v-card-text>
  </v-card>
  <!-- <v-textarea v-model="text"></v-textarea> -->
</template>

<script lang="ts">
import { mapState, mapActions } from "pinia";
import { useAppStore } from "@/store/app";
import axios from "axios";
export default {
  props: ["urn"],
  data() {
    return {
      tab: null,
      schemas: null,
      text: this.urn,
    };
  },
  mounted() {
    this.fetchSchemas();
  },
  computed: {
    versions() {
      if (this.schemas) {
        return Object.keys(this.schemas);
      } else {
        return [];
      }
    },
    ...mapState(useAppStore, ["api_base_path"]),
  },
  methods: {
    async fetchSchemas() {
      const response = await axios.get(
        `${this.api_base_path}/schema/${this.urn}?all_versions=true`
      );
      this.schemas = response.data;
    },
  },
};
</script>
