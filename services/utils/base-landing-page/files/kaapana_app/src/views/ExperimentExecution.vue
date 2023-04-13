<template>
  <v-container text-left fluid>
    <workflow-execution></workflow-execution>
  </v-container>
</template>

<script>
import Vue from "vue";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

import WorkflowExecution  from "@/components/WorkflowExecution.vue";


export default Vue.extend({
  components: {
    WorkflowExecution,
  },
  data: () => ({
  }),
  created() {
  },
  mounted () {console.log("Hello, I am the Experiment Execution View!")
  },
  watch: {
  },
  computed: {
  },
  methods: {
  },
});
</script>

<style lang="scss">

</style>
