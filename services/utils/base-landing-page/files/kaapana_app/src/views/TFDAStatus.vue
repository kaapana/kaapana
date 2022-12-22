<template>
  <v-container>
    <v-text-field
      v-model="search"
      label="Search"
      single-line
      hide-details
    ></v-text-field>
    <v-layout v-resize="onResize" column style="padding-top: 56px">
      <div id="app">
        <h1 class="title my-3" align="left">Status Updates</h1>
        
        {{ finaMinioBuckets}}
    </v-layout>
    
  </v-container>
  
</template>
 


<script lang="ts">
import Vue from "vue";
import request from "@/request";
import { mapGetters } from "vuex";
import storage from "local-storage-fallback";
import kaapanaApiService from "@/common/kaapanaApi.service";
import { LOGIN, LOGOUT, CHECK_AUTH } from "@/store/actions.type";
import axios from "axios";

export default Vue.extend({
  data: () => ({
    singleSelect: false,
    singleSelects: true,
    datasetInformation: [],
    installedWorkflow: [] as any,
    availableCharts: [] as any,
    finaMinioBuckets: [] as any,

    checkbox: false,

    search: "",
    dialog: false,
  }),
  mounted() {
    this.getMinioBuckets();
  },

  methods: {
    login() {
      this.$store
        .dispatch(LOGIN)
        .then(() => this.$router.push({ name: "home" }));
    },
    logout() {
      this.$store.dispatch(LOGOUT);
    },

    getMinioBuckets() {
      const getStatus = "/backend/api/v1/minio/tfda-post-status/";

      request
        .get(getStatus)
        .then((response: any) => {
          const bucketsList = JSON.stringify(response.data);
          console.log(response.data);

          this.finaMinioBuckets = response.data;
        })
        .catch((err: any) => {
          console.log(err);
        });
    },

    onResize() {},
  },
});
</script>

<style lang="scss">
a {
  text-decoration: none;
}
#preview {
  padding: 10px 20px;
  border: 1px dotted #ccc;
  margin: 30px 0;
}
</style>