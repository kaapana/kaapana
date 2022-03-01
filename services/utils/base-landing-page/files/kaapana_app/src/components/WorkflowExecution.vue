
<template lang="pug">
v-card
  v-form(v-model="valid", ref="executeWorkflow", lazy-validation)
    v-card-title
      span.text-h5 Workflow Execution
    v-card-text
      v-container
        v-row
          //- v-col(cols='12')
          //-   v-select(v-model='clientPost.allowed_dags' :items='dags' label='Allowed dags' multiple='' chips='' hint='Which dags are allowed to be triggered' persistent-hint='')
          //- v-col(cols='12')
          //-   v-select(v-model='clientPost.allowed_datasets' :items='datasets' label='Allowed datasets' multiple='' chips='' hint='Which datasets are allowed to be triggered' persistent-hint='')
          v-col(cols="12")
            v-jsf(v-model="workflowPayload", :schema="schema")
          v-col(cols="12")
            p {{ workflowPayload }}
    v-card-actions
      v-btn(color="orange", @click="submitWorkflow()", rounded, dark) Submit job
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";
import VJsf from "@koumoul/vjsf/lib/VJsf.js";
import "@koumoul/vjsf/lib/VJsf.css";
import "@koumoul/vjsf/lib/deps/third-party.js";

export default {
  name: "WorkflowExecution",
  components: {
    VJsf,
  },
  data: () => ({
    valid: false,
    workflowPayload: {},
    schema: {}
  }),
  props: {
    instance: {
      type: Object,
      required: true,
    },
    remote: {
      type: Boolean,
      required: true,
    },
  },
  mounted() {
    this.getSchema()
  },
  // watch: {
  //   dialog (val) {
  //     val || this.close()
  //   },
  //   dialogDelete (val) {
  //     val || this.closeDelete()
  //   },
  //   },
  methods: {
    getSchema() {
      kaapanaApiService
        .federatedClientApiGet("/workflow-json-schema")
        .then((response) => {
          this.schema = response.data;
        })
        .catch((err) => {
          console.log(err);
        });
    },
    submitWorkflow() {
      kaapanaApiService
        .federatedClientApiPost("/submit-workflow-json-schema", {
          data: this.workflowPayload,
        })
        .then((response) => {
          console.log(response);
        })
        .catch((err) => {
          console.log(err);
        });
    },
  },
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">
</style>
