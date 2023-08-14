<template>
  <div>
    <button @click="accept">Accept</button>
    <button @click="reject">Reject</button>
  </div>
</template>

<script>
export default {
  methods: {
    accept() {
      // Handle accept logic here
      console.log('Accepted');
    },
    reject() {
      // Handle reject logic here
      console.log('Rejected');
    }
  }
}
</script>

<style>
/* You can add some basic styling here if needed */
button {
  padding: 10px 20px;
  margin: 5px;
}
</style>

<!-- <template lang="pug">
  //- <div>
  //-   <button @click="accept">Accept</button>
  //-   <button @click="reject">Reject</button>
  //- </div>
  v-container(text-left fluid)
    v-col(cols="9")
      div(v-if="this.tree.length == 0")
        h1 Workflow results 
        p Results from the workflows will be shown here!

</template>

<script>
import Vue from 'vue'
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

import IFrameWindow from "@/components/IFrameWindow.vue";
export default {
  methods: {
    accept() {
      // Handle accept logic here
      console.log('Accepted');
    },
    reject() {
      // Handle reject logic here
      console.log('Rejected');
    }
  }
}
</script>

<style>
/* You can add some basic styling here if needed */
button {
  padding: 10px 20px;
  margin: 5px;
}
</style> -->