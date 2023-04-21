
<template>
  <v-card>
    <v-form 
      v-model="valid"
      ref="executeWorkflow"
      lazy-validation
    >
      <v-card-title>
        <h5>Experiment Execution</h5>
      </v-card-title>
      <v-card-text>
        <v-container>
          <!-- Instance: check if experiment is started on local or remote instance -->
          <v-row>
            <v-row v-if="remote_instance_names.length">
              <!-- remote instances registered -> offer switch -->
              <v-col align="center">
                <v-switch 
                  v-model="local_remote_switch" 
                  :label="switch_label()"
                ></v-switch>
              </v-col>
              <v-col v-if="remote, !local_remote_switch" cols="12">
                <v-select 
                  v-model="instance_names" 
                  :items="remote_instance_names" 
                  label="Remote instances" 
                  multiple="" 
                  chips="" 
                  hint="On which instances do you want to execute the workflow"
                ></v-select>
              </v-col>
            </v-row>
            <v-row v-else="v-else">
              <!-- no remote instances registered -> just display that local instance is used -->
              <v-col align="left">
                <p class="text-body-1">
                  <!-- switch_label() also adds client_instance to instance_names -->
                  {{ switch_label() }}
                </p>
              </v-col>
            </v-row>
          </v-row>
          <!-- DAG: select dag -->
          <v-row>
            <v-col v-if="instance_names.length" cols="12">
              <v-select 
                v-model="dag_id" 
                :items="available_dags" 
                label="DAGs" 
                chips="" 
                hint="Select a dag" 
                :rules="dagRules()"
                required
              ></v-select>
            </v-col>
          </v-row>
          <!-- Experiment name -->
          <v-row v-if="dag_id">
            <v-col cols="12">
              <v-text-field
                label="Experiment name" 
                v-model="experiment_name" 
                :rules="experimentnameRules()" 
                required
              ></v-text-field>
            </v-col>
            <!-- don't do exp_id rn-->
          </v-row>
          <!-- Data- and Workflow forms -->
          <v-row v-if="experiment_name">
            <v-col v-for="(schema, name) in schemas" cols="12">
              <p>{{name}}</p>
              <v-jsf 
                v-model="formData[name]" 
                :schema="schema" 
                required="required"
              ></v-jsf>
            </v-col>
          </v-row>
          <!-- Select remote instance for remote workflow -->
          <v-row v-if="remote_instances_w_external_dag_available.length">
            <v-col cols="12">
              <h3>Remote Workflow</h3>
            </v-col>
            <v-col cols="12">
              <v-select 
                v-model="selected_remote_instances_w_external_dag_available" 
                :items="remote_instances_w_external_dag_available" 
                label="External Instance names" 
                multiple="" 
                chips="" 
                hint="On which (remote) nodes do you want to execute the workflow"
              ></v-select>
            </v-col>
          </v-row>
          <!-- Forms of external workflows -->
          <v-row v-if="Object.keys(external_schemas).length">
            <v-col v-for="(schema, name) in external_schemas" cols="12">
              <p>{{name}}</p>
              <v-jsf 
                v-model="formData['external_schema_' + name]" 
                :schema="schema" 
                required="required"
              ></v-jsf>
            </v-col>
          </v-row>
          <!-- Conf data summarizing the configured experiment -->
          <v-row>
            <v-col cols="12">
              <v-tooltip v-model="showConfData" top="">
                <template v-slot:activator="{ on, attrs }">
                  <v-btn icon="" v-bind="attrs" v-on="on">
                    <v-icon color="grey lighten-1">mdi-email</v-icon>
                  </v-btn>
                </template>
                <pre class="text-left">Experiment name: {{experiment_name}}</pre>
                <pre class="text-left">Dag id: {{dag_id}}</pre>
                <pre class="text-left">Instance name: {{instance_names}}</pre>
                <pre class="text-left">External instance name: {{selected_remote_instances_w_external_dag_available}}</pre>
                <pre class="text-left">{{ formDataFormatted }}</pre>
              </v-tooltip>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-btn 
          color="primary" 
          @click="submissionValidator()" 
          dark="dark"
        >
          Start Experiment
        </v-btn>
        <v-btn 
          color="primary" 
          @click="(instance_names=[]) 
          &amp;&amp; 
          (dag_id=null)" 
          dark="dark"
        >
          Clear
        </v-btn>
      </v-card-actions>
    </v-form>
  </v-card>
</template>
  
<script>
  import { mapGetters } from "vuex";
  import kaapanaApiService from "@/common/kaapanaApi.service";
  import VJsf from "@koumoul/vjsf/lib/VJsf.js";
  import "@koumoul/vjsf/lib/VJsf.css";
  import "@koumoul/vjsf/lib/deps/third-party.js";

  export default {
    name: "WorkflowExecution",
    components: {
      VJsf,
    },
    data() {
      return this.initialState();
    },
    props: {
    },
    created() {
    },
    mounted() {
      // console.log("Hello, I am the WorkflowExecution!");
      this.refreshClient();
    },
    watch: {
      // watcher for instances
      instance_names() {
        // reset dag_id and external_dag_id if instance changes
        this.dag_id = null
        this.external_dag_id = null

        this.getDags()
        this.resetFormData()
        this.getRemoteInstances()
        // this.getRemoteInstanceNames()
      },
      selected_remote_instances_w_external_dag_available() {
        this.resetExternalFormData()
        if (this.selected_remote_instances_w_external_dag_available.length) {
          this.getExternalUiFormSchemas()
        }
      },
      // watchers for dags
      dag_id(value) {
        this.resetFormData()
        this.experiment_name = value;
      },
      external_dag_id() {
        this.resetExternalFormData()
      },
      // other watchers
    },
    computed: {
      available_instance_names () {
        return this.instances.map(({ instance_name }) => instance_name);
      },
      formDataFormatted () {
        return this.formatFormData(this.formData)
      },
    },
    computed: {
      ...mapGetters(['currentUser', 'isAuthenticated'])
    },
    methods: {
      initialState() {
        return {
          // UI stuff
          valid: false,
          local_remote_switch: true,
          // instances
          clientInstance: {},
          instance_names: [],
          all_instance_names: [],
          remote: true,
          remoteInstances: {},
          remote_instance_names: [],
          selected_remote_instances_w_external_dag_available: [],
          remote_instances_w_external_dag_available: [],
          // DAGs
          dag_id: null,
          available_dags: [],
          external_dag_id: null,
          // form stuff
          formData: {},
          formDataFormatted: {},
          schemas: {},
          external_schemas: {},
          // validation stuff
          // other stuff
          experiment_name: null, // or to ''
          showConfData: false,
        }
      },
      reset() {
          Object.assign(this.$data, this.initialState());
          this.refreshClient();
      },
      refreshClient() {
        this.getClientInstance()
        this.getRemoteInstances()
      },
      switch_label() {
        if (this.local_remote_switch == true) {
          if ((this.instance_names.indexOf(this.clientInstance.instance_name) === -1) && 
              (this.clientInstance.instance_name !== undefined)) {
            this.instance_names.push(this.clientInstance.instance_name)
          } 
          return `Local experiment on instance: ${this.clientInstance.instance_name}`
        }
        else {
          if (this.instance_names.indexOf(this.clientInstance.instance_name) !== -1) {
            this.instance_names = []
          }
          return `Remote Experiment on available remote instances`
        }
      },
      // methods for form rendering
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
        this.selected_remote_instances_w_external_dag_available = []
      },
      resetExternalFormData() {
        this.external_schemas = {}
        this.remote_instances_w_external_dag_available = []
        // this.remote_instance_names = []  // if not commented out, remote instance not displayed anymore in experiment_form
        if (this.external_dag_id != null) {
          console.log('getting')
          this.getRemoteInstancesWithExternalDagAvailable()
        } else {
        }
        Object.entries(this.formData).forEach(([key, value]) => {
          if (key.startsWith('external_schema_') && (key != ('external_schema_federated_form'))) {
            console.log(`Deleting ${key}: ${value}`)
            delete this.formData[key]
          }
        });
      },
      // other methods
      dagRules() {
        return [
          (v) => !!v || "DAG is required",
        ];
      },
      experimentnameRules() {
        return [
          (v) => !!v || "Experiment name is required",
        ];
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

      // API Calls: Instances
      getClientInstance() {
        kaapanaApiService
          .federatedClientApiGet("/client-kaapana-instance")
          .then((response) => {
            this.clientInstance = response.data;
            if ((this.all_instance_names.indexOf(this.clientInstance.instance_name) === -1) && 
              (this.clientInstance !== undefined)) {
              this.allInstances.push(this.clientInstance)
              this.all_instance_names.push(this.clientInstance.instance_name)
            }
          })
          .catch((err) => {
            console.log(err);
            // this.clientInstance = {} // doesn't make sense 
          });
      },
      getRemoteInstances() {
        kaapanaApiService
          .federatedClientApiPost("/get-remote-kaapana-instances")
          .then((response) => {
            this.remoteInstances = response.data;
            this.remote_instance_names = response.data.map(({ instance_name }) => instance_name);
            this.remoteInstances.forEach(remote_instance => {
              if (this.all_instance_names.indexOf(remote_instance.instance_name) === -1) {
                this.allInstances.push(remote_instance)
                this.all_instance_names.push(remote_instance.instance_name)
              }
            })
          })
          .catch((err) => {
            console.log(err);
          });
      },
      getRemoteInstancesWithExternalDagAvailable() {
        kaapanaApiService
          .federatedClientApiPost("/get-remote-kaapana-instances", {dag_id: this.external_dag_id})
          .then((response) => {
            this.remote_instances_w_external_dag_available = response.data.map(({ instance_name }) => instance_name)
            // this.addLocalInstanceForRemoteExecution()
          })
          .catch((err) => {
            console.log(err);
          });
      },
      // API Calls: Schemas
      getUiFormSchemas() {
        // remove 'undefined' from instance_names list

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
          .federatedClientApiPost("/get-ui-form-schemas",  {remote: true, experiment_name: this.experiment_name, dag_id: this.external_dag_id, instance_names: this.selected_remote_instances_w_external_dag_available})
          .then((response) => {
            this.external_schemas = response.data
          })
          .catch((err) => {
            console.log(err);
          });
      },
      // other API Calls
      getDags() { // might need a 2nd getDags() API call ?!
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
      submitWorkflow() {
        // modify attributes remote_data and federated_data depending on instances
        this.federated_data = false;
        if ((this.instance_names.indexOf(this.clientInstance.instance_name) != -1) && (this.instance_names.length == 1)) {
          // clientInstance is in instance_names ==> local experiment
          this.remote_data = false;
        } else {
          // clientInstance is not in instance_names ==> remote experiment
          this.remote_data = true;
        }
        if (this.selected_remote_instances_w_external_dag_available.length) {
          this.formData['external_schema_instance_names'] = this.selected_remote_instances_w_external_dag_available
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
            this.$router.push({ name: 'experiments' });
            this.$notify({
              type: 'success',
              title: "Experiment successfully created!",
            })
            this.reset()
          })
          .catch((err) => {
            console.log(err);
            this.$notify({
              type: 'error',
              title: "An error occured during the experiment creation!",
            })
          });
      }
    },
  };
  </script>

  <!-- Add "scoped" attribute to limit CSS to this component only -->
  <style scoped lang="scss">
    .is-invalid {
      border: 1px solid red;
    }
  </style>
