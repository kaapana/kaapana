<template>
  <v-container w-50 text-left fluid>
    <v-row justify="center">
      <v-col sm="12" md="6" xl="4" >
        <workflow-execution></workflow-execution>
      </v-col>
    </v-row>
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
