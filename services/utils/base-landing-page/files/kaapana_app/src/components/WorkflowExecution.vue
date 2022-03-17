
<template lang="pug">
  v-dialog(v-model='dialogOpen' max-width='600px')
    template(v-slot:activator='{ on, attrs }')
      v-btn(color='orange' v-bind='attrs' v-on='on' rounded dark) Execute workflow
    v-card
      v-form(v-model="valid", ref="executeWorkflow", lazy-validation)
        v-card-title
          span.text-h5 Workflow Execution
        v-card-text
          v-container
            //- v-row
            //-   v-col(v-if="remote" cols='12')
            //-     v-select(v-model='node_ids' :items='available_node_ids' label='Node ids' multiple='' chips='' hint='On which nodes do you want to execute the workflow')
            //-   v-col(v-if="node_ids.length" cols='12')
            //-     v-select(v-model='dag_id' :items='available_dags' label='Dags' chips='' hint='Select a dag')
            //-   v-col(v-for="(schema, name) in schemas" cols='12' v-if="!(remote==false && name=='federated_form')")
            //-     p {{name}}
            //-     v-jsf( v-model="formData[name]" :schema="schema")
            //-   p {{formData}}

            v-row
              v-col(v-if="remote" cols='12')
                v-select(v-model='node_ids' :items='available_node_ids' label='Node ids' multiple='' chips='' hint='On which nodes do you want to execute the workflow')
              v-col(v-if="node_ids.length" cols='12')
                v-select(v-model='dag_id' :items='available_dags' label='Dags' chips='' hint='Select a dag')
              //- v-if="!(remote==false && name=='federated_form')"
              v-col(v-for="(schema, name) in schemas" cols='12')
                p {{name}}
                v-jsf(v-model="formData[name]" :schema="schema")
            v-row(v-if="external_available_node_ids.length")
              v-col(cols='12')
                h3 Remote Workflow
              v-col(cols='12')
                v-select(v-model='external_node_ids' :items='external_available_node_ids' label='Node ids' multiple='' chips='' hint='On which nodes do you want to execute the workflow')
            v-row(v-if="Object.keys(external_schemas).length")
              v-col(v-for="(schema, name) in external_schemas" cols='12')
                p {{name}}
                v-jsf(v-model="formData['external_schema_' + name]" :schema="schema")
            v-row
              v-col(cols='12')
                v-tooltip(v-model='showConfData' top='')
                  template(v-slot:activator='{ on, attrs }')
                    v-btn(icon='' v-bind='attrs' v-on='on')
                      v-icon(color='grey lighten-1')
                        | mdi-email
                  pre.text-left Dag id: {{dag_id}}
                  pre.text-left Node id: {{node_ids}}
                  pre.text-left External node id: {{external_node_ids}}
                  pre.text-left {{ formData }}
        v-card-actions
          v-btn(color="orange", @click="submitWorkflow()" rounded dark) Submit job
          v-btn(color="orange", @click="(node_ids=[]) && (dag_id=null)" rounded dark) Clear
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
    dialogOpen: false,
    schemas: {},
    external_schemas: {},
    formData: {},
    available_dags: [],
    node_ids: [],
    external_node_ids: [],
    external_dag_id: null,
    external_available_node_ids: [],
    dag_id: null,
    showConfData: false,
  }),
  props: {
    remote: {
      type: Boolean,
      required: true,
    },
    instances: {
      type: Array,
      required: true
    }
  },
  computed: {
    available_node_ids () {
      return this.instances.map(({ node_id }) => node_id);
    },
  },
  mounted() {
  },
  watch: {
    dialogOpen () {
      this.node_ids = []
      this.dag_id = null
    },
    node_ids() {
      this.getDags()
      this.resetFormData()
    },
    dag_id() {
      this.resetFormData()
    },
    external_dag_id() {
      this.resetExternalFormData()
    },
    external_node_ids() {
      this.resetExternalFormData()
      if (this.external_node_ids.length) {
        this.getExternalUiFormSchemas()
      }
    }
  },
  methods: {
    resetFormData() {
      this.schemas = {}
      this.formData = {}
      if (this.remote == false) {
        this.node_ids = this.available_node_ids
      }
      this.resetExternalFormData()
      this.getUiFormSchemas()
      this.external_node_ids = []
    },
    resetExternalFormData() {
      this.external_schemas = {}
      this.external_available_node_ids = []
      if (this.external_dag_id != null) {
        console.log('getting')
        this.getAvailableExternalNodeIds()
      } else {
      }
      Object.entries(this.formData).forEach(([key, value]) => {
        if (key.startsWith('external_schema_') && (key != ('external_schema_federated_form'))) {
          console.log(`Deleting ${key}: ${value}`)
          delete this.formData[key]
        }
      });

    },
    getUiFormSchemas() {
      kaapanaApiService
        .federatedSchemaApiPost("/get-ui-form-schemas", {remote: this.remote, dag_id: this.dag_id, node_ids: this.node_ids})
        .then((response) => {
          let schemas = response.data
          if (this.remote==false && 'external_schemas' in schemas) {
            this.external_dag_id = schemas["external_schemas"]
            delete schemas.external_schemas
          } else {
            this.external_dag_id = null
          }
          this.schemas = schemas
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getExternalUiFormSchemas() {
      kaapanaApiService
        .federatedSchemaApiPost("/get-ui-form-schemas",  {remote: true, dag_id: this.external_dag_id, node_ids: this.external_node_ids})
        .then((response) => {
          this.external_schemas = response.data
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getDags() {
      kaapanaApiService
        .federatedClientApiPost("/get-dags", {remote: this.remote, node_ids: this.node_ids})
        .then((response) => {
          this.available_dags = response.data;
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getAvailableExternalNodeIds() {
      kaapanaApiService
        .federatedClientApiPost("/get-remote-kaapana-instances", {dag_id: this.external_dag_id})
        .then((response) => {
          this.external_available_node_ids = response.data.map(({ node_id }) => node_id);
        })
        .catch((err) => {
          console.log(err);
        });
    },
    submitWorkflow() {
      if (this.external_node_ids.length) {
        this.formData['external_schema_node_ids'] = this.external_node_ids
      }
      kaapanaApiService
        .federatedClientApiPost("/submit-workflow-schema", {
          dag_id: this.dag_id,
          node_ids: this.node_ids,          
          form_data: this.formData,
          remote: this.remote
        })
        .then((response) => {
          this.dialogOpen = false
          console.log(response);
        })
        .catch((err) => {
          console.log(err);
        });
    }
  }
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">
</style>
