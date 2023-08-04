<template>
  <v-container>
    <v-row>
      <v-col><div class="text-h4">Lookup URN Resources</div></v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-text-field
          v-model="urn_input"
          placeholder="urn:kaapana:experiment"
          clearable
          @keydown.enter.prevent="openURN"
          label="URN"
        >
        </v-text-field>
      </v-col>
      <v-col cols="auto">
        <v-btn
          block
          class="mt-2"
          @click="openURN"
          density="compact"
          icon="mdi-magnify"
          size="large"
        ></v-btn>
      </v-col>
    </v-row>
    <v-row>
      <v-container v-if="url">
        <v-row>
          <v-col cols="auto">Link:</v-col>
          <v-col
            ><a v-bind:href="url">{{ url }}</a></v-col
          >
        </v-row>
      </v-container>
    </v-row>
  </v-container>
  <iframe v-bind:src="view_url" width="100%" height="100%"></iframe>
</template>

<!-- <script lang="ts" setup> -->
<script lang="ts">
import { mapState } from "pinia";
import { useAppStore } from "@/store/app";

export default {
  computed: {
    ...mapState(useAppStore, ["api_base_path"]),
  },
  data() {
    return {
      urn_input: this.urn,
      url: "",
      view_url: "",
    };
  },
  methods: {
    openURN() {
      this.view_url = `${this.api_base_path}/urn/${this.urn_input}/viewer`;
      this.url = `${this.api_base_path}/urn/${this.urn_input}`;
    },
  },
  props: ["urn"],
};
</script>
