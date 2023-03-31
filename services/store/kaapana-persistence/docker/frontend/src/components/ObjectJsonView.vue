<template>
  <!-- <v-progress-circular indeterminate v-if="!object"></v-progress-circular> -->
  <v-card v-if="object">
    <!-- <v-tabs v-model="tab">
      <v-tag :value="version" v-for="version in Object.keys(object[0])">{{ version }}</v-tag>
    </v-tabs> -->
    <v-card-text>
      <v-textarea
        rows="40"
        variant="outlined"
        :value="JSON.stringify(object[0], null, 2)"
      ></v-textarea>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import axios from "axios";
import { mapState } from "pinia";
import { useAppStore } from "@/store/app";
export default {
  props: ["urn"],
  data() {
    return {
      object: undefined,
      tab: undefined,
    };
  },
  mounted() {
    this.fetchObject();
  },
  computed: {
    ...mapState(useAppStore, ["api_base_path"]),
  },
  methods: {
    async fetchObject() {
      const response = await axios.get(
        `${this.api_base_path}/object/${this.urn}`
      );
      this.object = response.data;
      console.log(this.object);
    },
  },
};
</script>
