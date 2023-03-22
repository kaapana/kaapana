
<template lang="pug">
v-dialog(v-model='dialogOpen' max-width='600px')
  template(v-slot:activator='{ on, attrs }')
    v-tooltip(bottom)
      template(v-slot:activator="{ on }")
        v-btn(v-bind='attrs' v-on='on' color="primary" @click="dialogOpen = true" x-large small icon dark)
          v-icon(class="mx-2" x-large) mdi-play-circle
      span Start Experiment
  v-card
    v-form(v-model="valid", ref="executeWorkflow", lazy-validation)
      v-card-title
        span.text-h5 Experiment Execution
      v-card-text
        v-container
          //- Instance: check if experiment is started on local or remote instance
          v-row
            v-row(v-if="remote_instance_names.length")
              //- remote instances registered --> offer switch
              v-col(align="center")
                v-switch(v-model="local_remote_switch" :label="switch_label()")
              v-col(v-if="remote, !local_remote_switch" cols='12')
                v-select(v-model='instance_names' :items='remote_instance_names' label='Remote instances' multiple='' chips='' hint='On which instances do you want to execute the workflow')
            v-row(v-else)
              //- no remote instances registered --> just display that local instance is used
              v-col(align="left")
                //- switch_label() also adds client_instance to instance_names
                p(class="text-body-1") {{ switch_label() }}
          //- DAG: select dag
          v-row
            v-col(v-if="instance_names.length" cols='12')
              v-select(v-model='dag_id' :items='available_dags' label='DAGs' chips='' hint='Select a dag' :rules="dagRules" required)
          //- Experiment name
          v-row(v-if="dag_id")
            v-col(cols='12')
              //- v-text-field(v-model='experiment_name' label='Experiment name' required='')
              //-  required='' clearable
              v-text-field(label="Experiment name" v-model="experiment_name_wID" :rules="experimentnameRules" required)
            //- don't do exp_id rn
          //- Data- and Workflow forms
          v-row(v-if="experiment_name")
            //- :rules="dataformRules" required)
            v-col(v-for="(schema, name) in schemas" cols='12')
              p {{name}}
              //- v-jsf(v-model="formData[name]" :schema="schema" v-bind:class="{ 'is-invalid': !validateFormData(schema, formData[name]) }" required)
              v-jsf(v-model="formData[name]" :schema="schema" required)
          v-row(v-if="external_available_instance_names.length")
            v-col(cols='12')
              h3 Remote Workflow
            v-col(cols='12')
              v-select(v-model='external_instance_names' :items='external_available_instance_names' label='External Instance names' multiple='' chips='' hint='On which (remote) nodes do you want to execute the workflow')
          v-row(v-if="Object.keys(external_schemas).length")
            v-col(v-for="(schema, name) in external_schemas" cols='12')
              p {{name}}
              v-jsf(v-model="formData['external_schema_' + name]" :schema="schema" required)
          v-row
            v-col(cols='12')
              v-tooltip(v-model='showConfData' top='')
                template(v-slot:activator='{ on, attrs }')
                  v-btn(icon='' v-bind='attrs' v-on='on')
                    v-icon(color='grey lighten-1')
                      | mdi-email
                pre.text-left Experiment name: {{experiment_name}}
                pre.text-left Dag id: {{dag_id}}
                pre.text-left Instance name: {{instance_names}}
                pre.text-left External instance name: {{external_instance_names}}
                pre.text-left {{ formDataFormatted }}
      v-card-actions
        v-btn(color="primary", @click="submissionValidator()"  dark) Start Experiment
        v-btn(color="primary", @click="(instance_names=[]) && (dag_id=null)"  dark) Clear
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
    schemas: {},          // changed from {} to [] since we're getting a string and no object
    external_schemas: {}, // changed from {} to [] since we're getting a string and no object
    formData: {},
    available_dags: [],
    instance_names: [],
    external_instance_names: [],
    external_dag_id: null,
    external_available_instance_names: [],
    remote_instance_names: [],
    dag_id: null,
    experiment_name: '',
    experiment_id: null, // Math.random().toString(20).substr(2, 6), // new Date().getTime(),
    showConfData: false,
    federated_data: false,
    remote_data: false,
    local_remote_switch: true,
    form_requiredFields: [],
    my_form_validation: false,
    form_validation_cohort_name: false,
    form_validation_method_confirmation: false
  }),
  props: {
    remote: {
      type: Boolean,
      required: true,
    },
    instances: {
      type: Array,
      required: true
    },
    clientinstance: {
      type: Object,
      required: true,
    }
  },
  created() {
  },
  computed: {
    available_instance_names () {
      return this.instances.map(({ instance_name }) => instance_name);
    },
    formDataFormatted () {
      return this.formatFormData(this.formData)
    },
    experiment_name_wID: {
      get() {
        return `${this.dag_id}_${this.experiment_id}`;
      },
      set(value) {
        this.experiment_name = value;
      }
    },
    dagRules() {
      return [
        (v) => !!v || "DAG is required",
        // (v) => (v && v.length <= 20) || "Name must be less than or equal to 20 characters",
      ];
    },
    experimentnameRules() {
      return [
        (v) => !!v || "Experiment name is required",
      ];
    },
    // dataformRules() {
    //   return [
    //     (v['data_form']['cohort']) => !!v['data_form']['cohort'] || "Cohort is required"
    //     // (v) => !!v || "Cohort is required",
    //   ];
    // }
  },
  mounted() {
  },
  watch: {
    dialogOpen () {
      this.instance_names = [];
      this.experiment_name = null
      this.experiment_id = this.experiment_id = Math.random().toString(20).substr(2, 6)
      this.dag_id = null
      this.external_instance_names = []
      this.local_remote_switch = true
    },
    instance_names() {
      this.getDags()
      this.resetFormData()
      this.getRemoteInstanceNames()
    },
    // doesn't make any sense anymore, since experiment_name is intended to be changed from default
    // experiment_name() {
    //   this.resetFormData()
    // },
    
    experiment_name_wID(value) {
      this.experiment_name = value;
    },
    dag_id() {
      this.resetFormData()
    },
    external_dag_id() {
      this.resetExternalFormData()
    },
    external_instance_names() {
      this.resetExternalFormData()
      if (this.external_instance_names.length) {
        this.getExternalUiFormSchemas()
      }
    }
  },
  methods: {
    switch_label() {
      if (this.local_remote_switch == true) {
        if (this.instance_names.indexOf(this.clientinstance.instance_name) === -1) {
          this.instance_names.push(this.clientinstance.instance_name)
        } 
        return `Local experiment on instance: ${this.clientinstance.instance_name}`
      }
      else {
        if (this.instance_names.indexOf(this.clientinstance.instance_name) !== -1) {
          this.instance_names = []
        }
        return `Remote Experiment on available remote instances` 
      }
    },
    formatFormData (formData) {
      // Only necessary because vjsf does not allow to have same keys in selection form with dependencies
      let formDataFormatted = {}
      Object.entries(formData).forEach(([form_key, form_value]) => {
        if (form_key == "workflow_form") {
          formDataFormatted[form_key] = {}
          Object.entries(form_value).forEach(([key, value]) => {
            formDataFormatted[form_key][key.split('#')[0]] = value
          });
        } else {
          formDataFormatted[form_key] = form_value
        }
      });
      return formDataFormatted
    },
    resetFormData() {
      this.schemas = {}
      this.formData = {}
      if (this.remote == false) {
        this.instance_names = this.available_instance_names
      }
      this.resetExternalFormData()
      this.getUiFormSchemas()
      this.external_instance_names = []
    },
    resetExternalFormData() {
      this.external_schemas = {}
      this.external_available_instance_names = []
      // this.remote_instance_names = []  // if not commented out, remote instance not displayed anymore in experiment_form
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
        .federatedClientApiPost("/get-ui-form-schemas", {remote: this.remote, experiment_name: this.experiment_name, dag_id: this.dag_id, instance_names: this.instance_names})
        .then((response) => {
          let schemas = response.data
          this.form_requiredFields = this.findRequiredFields(schemas)
          if ('external_schemas' in schemas) {
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
        .federatedClientApiPost("/get-ui-form-schemas",  {remote: true, experiment_name: this.experiment_name, dag_id: this.external_dag_id, instance_names: this.external_instance_names})
        .then((response) => {
          this.external_schemas = response.data
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getDags() {
      if (this.instance_names !== 0) {
        kaapanaApiService
          .federatedClientApiPost("/get-dags", {remote: this.remote, instance_names: this.instance_names})
          .then((response) => {
            this.available_dags = response.data;
          })
          .catch((err) => {
            console.log(err);
          });
      }
    },
    getAvailableExternalNodeIds() {
      kaapanaApiService
        .federatedClientApiPost("/get-remote-kaapana-instances", {dag_id: this.external_dag_id})
        .then((response) => {
          this.external_available_instance_names = response.data.map(({ instance_name }) => instance_name);
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getRemoteInstanceNames() {
      kaapanaApiService
        .federatedClientApiPost("/get-remote-kaapana-instances")
        .then((response) => {
          this.remote_instance_names = response.data.map(({ instance_name }) => instance_name);
        })
        .catch((err) => {
          console.log(err);
        });
    },
    findRequiredFields(obj, result = [], prefix = '') {
      for (const key in obj) {
        const value = obj[key];
        const fullKey = prefix ? `${prefix}.${key}` : key;
        if (value && typeof value === 'object') {
          this.findRequiredFields(value, result, fullKey);
        } else if (key === 'required' && !('default' in obj) && !('enum' in obj)) {
          // only add a required_field if no default value is defined and it's no 'enum' data type (special case for nnunet-predict)
          result.push(fullKey);
        }
      }
      return result;
    },
    submissionValidator() {
      let valid_check = []
      let invalid_fields = []
      if (this.$refs.executeWorkflow.validate()) { // validate dag_id and experiment_name in any cases
        // extract form name and attribute names of form_requiredFields
        for (let i=0; i<this.form_requiredFields.length; i++) {
          const req_field = this.form_requiredFields[i];
          const substrings = req_field.split(".");
          let form_name = "";
          let req_prop_name = "";
          for (let i = 0; i < substrings.length; i++) {
            if (i === 0) {
              form_name = substrings[i];
            } else if (substrings[i] === "required") {
              req_prop_name = substrings[i - 1];
              break;
            }
          }
          // find req_prop_name in form_name and check if valid
          if (this.formData[form_name].hasOwnProperty(req_prop_name)) {
            if (this.formData[form_name][req_prop_name]) {
              // valid value --> set indicator to true
              valid_check.push(true)
            } else {
              // inalid value --> set indicator to false
              valid_check.push(false)
              invalid_fields.push(req_prop_name)
            }
          }
          else {
            valid_check.push(false)
            invalid_fields.push(req_prop_name)
          }
        }
        if (valid_check.every(value => value === true)) {
          // all checks have been successful --> start experiment & return true
          this.submitWorkflow()
          return true
        } else {
          // NOT all checks have been successful --> return false
          const message = `Validation of form input values failed! Please set required values for ${invalid_fields.join(', ')}!`;
          this.$notify({
            type: 'error',
            title: message,
          })
          return false
        }
      } else {
        // NOT all checks have been successful --> return false
        const message = `Validation of form input values failed! Please set all required values!`;
        this.$notify({
          type: 'error',
          title: message,
        })
        return false
      }
    },
    submitWorkflow() {
      // modify attributes remote_data and federated_data depending on instances 
      this.federated_data = false;
      if ((this.instance_names.indexOf(this.clientinstance.instance_name) != -1) && (this.instance_names.length == 1)) {
        // clientinstance is in instance_names ==> local experiment
        this.remote_data = false;
      } else {
        // clientinstance is not in instance_names ==> remote experiment
        this.remote_data = true;
      }
      if (this.external_instance_names.length) {
        this.formData['external_schema_instance_names'] = this.external_instance_names
        this.federated_data = true
      }
      kaapanaApiService
        .federatedClientApiPost("/experiment", {
          experiment_name: this.experiment_name,
          dag_id: this.dag_id,
          instance_names: this.instance_names,          
          conf_data: this.formatFormData(this.formData),
          remote: this.remote_data,
          federated: this.federated_data,
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
  .is-invalid {
    border: 1px solid red;
  }
</style>
