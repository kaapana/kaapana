<template>
  <v-card>
    <v-form v-model="valid" ref="executeWorkflow" lazy-validation>
      <v-card-title class="d-flex justify-space-between">
        <h5>Workflow Execution</h5>
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn v-on="on" @click='getKaapanaInstances()' small icon>
              <v-icon color="primary" dark>
                mdi-refresh
              </v-icon> 
            </v-btn> 
          </template>
          <span>refresh Workflow Execution component</span>
        </v-tooltip>
      </v-card-title>
      <v-card-text>
        <v-container>
          <v-row v-if="available_kaapana_instance_names.length > 1">
            <v-icon color="primary" class="mx-2" small>mdi-home</v-icon>
            Local instance: {{ localKaapanaInstanceName }}
          </v-row>
          <v-row v-if="available_kaapana_instance_names.length > 1">
            <v-col cols="12">
              <v-select
                v-model="selected_kaapana_instance_names"
                :items="available_kaapana_instance_names"
                label="Runner instances"
                multiple
                chips
                hint="On which instances do you want to execute the workflow?"
              ></v-select>
            </v-col>
          </v-row>
          <!-- Federated workflow: yes/no? -->
          <v-row>
            <v-col cols="12" v-if="selected_kaapana_instance_names.length === 1 && selected_kaapana_instance_names[0] === localKaapanaInstanceName">
              <v-switch
                v-model="federated"
                label="Federated workflow"
              ></v-switch>
            </v-col>
          </v-row>
          <!-- Federation: federation selection if -->
          <v-row>
            <v-col cols="12" v-if="federated || (localKaapanaInstanceName && remoteInstanceSelected)">
              <v-select
                v-model="selected_federation_name"
                :items="available_federation_names"
                label="Federation"
                chips
                hint="Federation in which a federated workflow is executed."
                required
              ></v-select>
            </v-col>
          </v-row>
          <!-- DAG: select dag -->
          <v-row>
            <v-col cols="12" v-if="(available_dags.length && !federated) || (available_dags.length && federated && Object.entries(selected_federation_name).length !== 0)">
              <v-select
                v-if="selected_kaapana_instance_names.length"
                v-model="dag_id"
                :items="available_dags"
                label="Workflow"
                chips
                hint="Workflow to execute"
                :rules="dagRules()"
                required
              ></v-select>
            </v-col>
            <v-col cols="12" align="center" justify="center" v-else>
              <v-progress-circular
                indeterminate
                color="primary"
              ></v-progress-circular>
            </v-col>
          </v-row>
          <!-- Workflow name -->
          <v-row v-if="dag_id">
            <v-col cols="12">
              <v-text-field
                label="Workflow name"
                v-model="workflow_name"
                :rules="workflownameRules()"
                required
              ></v-text-field>
            </v-col>
            <!-- don't do workflow_id rn-->
          </v-row>
          <!-- Data- and Workflow forms -->
          <v-row v-if="datasets_available" :key="dag_id">
            <v-col v-for="(schema, name) in schemas" cols="12">
              <!-- <p>{{name}}</p> -->
              <v-jsf
                v-model="formData[name]"
                :schema="schema"
                required="required"
              ></v-jsf>
            </v-col>
          </v-row>
          <!-- Select remote instance for remote workflow -->
          <v-row v-show="remote_instances_w_external_dag_available.length">
            <v-col cols="12">
              <h3>Remote Workflow</h3>
            </v-col>
            <v-col cols="12">
              <v-select
                v-model="selected_remote_instances_w_external_dag_available"
                :items="remote_instances_w_external_dag_available"
                label="External Instance names"
                multiple
                chips
                hint="On which (remote) nodes do you want to execute the workflow"
              ></v-select>
            </v-col>
          </v-row>
          <!-- Forms of external workflows -->
          <v-row v-if="Object.keys(external_schemas).length">
            <v-col v-for="(schema, name) in external_schemas" cols="12">
              <p>{{ name }}</p>
              <v-jsf
                v-model="formData['external_schema_' + name]"
                :schema="schema"
                required="required"
              ></v-jsf>
            </v-col>
          </v-row>
          <!-- Conf data summarizing the configured workflow -->
          <v-row>
            <v-col cols="12">
              <v-tooltip v-model="showConfData" top>
                <template v-slot:activator="{ on, attrs }">
                  <v-btn icon v-bind="attrs" v-on="on">
                    <v-icon color="grey lighten-1">mdi-email</v-icon>
                  </v-btn>
                </template>
                <pre class="text-left">Workflow name: {{ workflow_name }}</pre>
                <pre class="text-left">Dag id: {{ dag_id }}</pre>
                <pre class="text-left">
                  Instance name: {{ selected_kaapana_instance_names }}
                </pre>
                <pre class="text-left">
                  External instance name: {{
                    selected_remote_instances_w_external_dag_available
                  }}
                </pre>
                <pre class="text-left">{{ formDataFormatted }}</pre>
              </v-tooltip>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-card-actions v-if="available_dags.length">
        <v-spacer></v-spacer>
        <v-btn color="primary" @click="submissionValidator()">
          Start Workflow
        </v-btn>
        <v-btn
          @click="isDialog ? cancel() : clearForm()"
        >
          {{ this.isDialog ? "Cancel" : "Clear" }}
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
    isDialog: {
      type: Boolean,
      default: false,
    },
    identifiers: {
      type: Array,
      default: () => [],
    },
    onlyLocal: {
      type: Boolean,
      default: false,
    },
    kind_of_workflows: {
      type: String,
      default: "all",
    },
  },
  created() {},
  mounted() {
    this.refreshClient();
    this.getFederations();
  },
  watch: {
    ///// watcher for instances
    available_kaapana_instance_names(value) {
      this.selected_kaapana_instance_names = [value[0]];
    },
    selected_kaapana_instance_names(value) {
      if (value.length === 0) {
        this.selected_kaapana_instance_names = [
          this.available_kaapana_instance_names[0],
        ];
      }
      console.log("this.selected_kaapana_instance_names: ", this.selected_kaapana_instance_names)
      this.getDags();
      this.getUiFormSchemas();
      // reset dag_id and external_dag_id if instance changes
      this.dag_id = null;
      this.external_dag_id = null;
    },
    selected_remote_instances_w_external_dag_available() {
      // this.resetExternalFormData()
      if (this.selected_remote_instances_w_external_dag_available.length) {
        this.getExternalUiFormSchemas();
      }
    },
    ///// watchers for dags
    dag_id(value) {
      // ensure that this.schemas_dict is there
      this.getUiFormSchemas();
      // forms
      this.formData = {};
      console.log("DAG_ID watcher value: ", value)
      if (value !== null) {
        this.workflow_name = value;
        // not directly set to this.schemas to avoid rerendering of components
        // copied to avoid changing the original schemas
        // get the schema of the selected workflow via dag_id
        // console.log("this.schemas_dict: ", this.schemas_dict)
        let schemas = JSON.parse(JSON.stringify(this.schemas_dict[value]));
        // if workflow triggered w/o dataset but directly via identifiers, delete schemas["data_form"]
        if (this.identifiers.length > 0) {
          delete schemas["data_form"];
        }
        this.form_requiredFields = this.findRequiredFields(schemas);
        // if workflow is a fl-orchestrator worklfow and triggers remotely other workflow, extract external_dag_id
        if ("external_schemas" in schemas) {
          this.external_dag_id = schemas["external_schemas"];
          delete schemas.external_schemas;
        } else {
          this.external_dag_id = null;
        }
        this.schemas = JSON.parse(JSON.stringify(schemas));
      } else {
        this.schemas = {};
        this.external_dag_id = null;
      }
      // data form
      this.datasets_available = true;
      console.log("this.schemas: ", this.schemas)
      if (this.schemas["data_form"]) {  // !== null 
        Object.entries(this.schemas["data_form"]).forEach(([key, value]) => {
          if ( key.startsWith("__emtpy__") ) {
            this.datasets_available = false;
            this.$notify({
              type: "error",
              title: "The selected runner instances have no common allowed datasets!",
            });
          }
        });
      }
      // functions have to be called after the schemas are set
    },
    external_dag_id() {
      this.external_schemas = {};
      if (this.external_dag_id != null) {
        // this.getKaapanaInstancesWithExternalDagAvailable();
        this.getFederatedPermissionProfiles(null, this.external_dag_id);
      } else {
        this.remote_instances_w_external_dag_available = [];
      }
      Object.entries(this.formData).forEach(([key, value]) => {
        if (
          key.startsWith("external_schema_") &&
          key != "external_schema_federated_form"
        ) {
          console.log(`Deleting ${key}: ${value}`);
          delete this.formData[key];
        }
      });
    },
    ///// other watchers
    federated() {
      // if (this.federated) {
      //   // get federations
      //   this.getFederations();
      // }
    },
    selected_federation_name() {
      // save selected federation to this.selected_federation
      console.log("this.available_federations: ", this.available_federations)
      console.log("this.selected_federation_name: ", this.selected_federation_name)
      this.selected_federation = this.available_federations.find((federation) => federation.federation_name === this.selected_federation_name)
      console.log("this.selected_federation: ", this.selected_federation)
      // get available_federated_permission_profile_ids of selected federation
      this.getFederatedPermissionProfiles(this.selected_federation.federation_id, null)
    }, 
    available_federated_permission_profile_ids() {
      // get DAGs as soon as available_federated_permission_profile_ids are defined
      this.getDags()
    }
  },
  computed: {
    ...mapGetters(["currentUser", "isAuthenticated"]),
    formDataFormatted() {
      return this.formatFormData(this.formData);
    },
    remoteInstanceSelected() {
      // returns True if selected_kaapana_instance_names contains a remote instance name
      return this.selected_kaapana_instance_names.some((item) => {
        return item !== this.localKaapanaInstanceName;
      });
    },

  },
  methods: {
    initialState() {
      return {
        // UI stuff
        valid: false,
        federated: false,
        // instances
        localKaapanaInstanceName: '',
        available_kaapana_instance_names: [],
        selected_kaapana_instance_names: [],
        selected_remote_instances_w_external_dag_available: [],
        remote_instances_w_external_dag_available: [],
        // federations
        available_federation_names: [],
        selected_federation_name: '',
        available_federations: [],
        selected_federation: {},
        // federated_permission_profiles
        available_federated_permission_profile_ids: [],
        available_federated_permission_profiles: [],
        selected_federated_permission_profile_ids: [],
        selected_federated_permission_profiles: [],
        // DAGs
        dag_id: null,
        available_dags: [],
        external_dag_id: null,
        // form stuff
        formData: {},
        schemas: {},
        schemas_dict: {},
        external_schemas: {},
        // validation stuff
        // other stuff
        workflow_name: null, // or to ''
        showConfData: false,
        datasets_available: true
      };
    },
    reset() {
      Object.assign(this.$data, this.initialState());
      this.refreshClient();
    },
    refreshClient() {
      this.getKaapanaInstances();
    },
    clearForm() {
      this.dag_id = null;
    },
    cancel() {
      this.$emit("cancel");
      this.reset();
    },
    // methods for form rendering
    formatFormData(formData) {
      // Only necessary because vjsf does not allow to have same keys in selection form with dependencies
      let formDataFormatted = {};
      Object.entries(formData).forEach(([form_key, form_value]) => {
        if (form_key == "workflow_form") {
          formDataFormatted[form_key] = {};
          Object.entries(form_value).forEach(([key, value]) => {
            formDataFormatted[form_key][key.split("#")[0]] = value;
          });
        } else {
          formDataFormatted[form_key] = form_value;
        }
      });
      return formDataFormatted;
    },
    // other methods
    dagRules() {
      return [(v) => !!v || "Workflow is required"];
    },
    workflownameRules() {
      return [(v) => !!v || "Workflow name is required"];
    },
    findRequiredFields(obj, result = [], prefix = "") {
      for (const key in obj) {
        const value = obj[key];
        const fullKey = prefix ? `${prefix}.${key}` : key;
        if (key === "oneOf") {
          continue;
        }
        if (value && typeof value === "object") {
          this.findRequiredFields(value, result, fullKey);
          // } else if (key === 'required' && !('default' in obj) && !('enum' in obj)) {
        } else if (key !== "readOnly" && key === "required" && !("enum" in obj)) {
          // only go here if it's no 'enum' data type (special case for nnunet-predict)
          result.push(fullKey);
        }
      }
      return result;
    },
    submissionValidator() {
      let valid_check = [];
      let invalid_fields = [];
      if ( this.datasets_available !== true) {
       // NOT all checks have been successful --> return false
       const message = "The selected runner instances have no common allowed datasets!";
        this.$notify({
          type: "error",
          title: message,
        });
        return false;
      }
      if (this.$refs.executeWorkflow.validate()) {
        // validate dag_id and workflow_name in any cases
        // extract form name and attribute names of form_requiredFields
        for (let i = 0; i < this.form_requiredFields.length; i++) {
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
              valid_check.push(true);
            } else {
              // inalid value --> set indicator to false
              valid_check.push(false);
              invalid_fields.push(req_prop_name);
            }
          } else {
            valid_check.push(false);
            invalid_fields.push(req_prop_name);
          }
        }
        if (valid_check.every((value) => value === true)) {
          // all checks have been successful --> start workflow & return true
          this.submitWorkflow();
          return true;
        } else {
          // NOT all checks have been successful --> return false
          const message = `Validation of form input values failed! Please set required values for ${invalid_fields.join(
            ", "
          )}!`;
          this.$notify({
            type: "error",
            title: message,
          });
          return false;
        }
      } else {
        // NOT all checks have been successful --> return false
        const message = `Validation of form input values failed! Please set all required values!`;
        this.$notify({
          type: "error",
          title: message,
        });
        return false;
      }
    },
    ///// GET API Calls
    getKaapanaInstances() {
      kaapanaApiService
        .federatedClientApiPost("/get-kaapana-instances")
        .then((response) => {
          this.available_kaapana_instance_names = response.data
            .filter((instance) => {
              if (this.onlyLocal) {
                return !instance.remote;
              }
              // just return local and all remote instances regardless of tehir allowed_dags
              return instance
              // return instance.allowed_dags.length !== 0 || !instance.remote;
            })
            .map(({ instance_name }) => instance_name);
          this.localKaapanaInstanceName = response.data
            .filter((instance) => {
              return !instance.remote;
            })
            .map(({ instance_name }) => instance_name)[0];
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getKaapanaInstancesWithExternalDagAvailable() {
      kaapanaApiService
        .federatedClientApiPost("/get-kaapana-instances", {
          dag_id: this.external_dag_id,
        })
        .then((response) => {
          this.remote_instances_w_external_dag_available = response.data.map(
            ({ instance_name }) => instance_name
          );
          if (this.remote_instances_w_external_dag_available.length === 0) {
            this.$notify({
              title: `No registered remote instance with ${this.external_dag_id} as allowed DAG.`,
              type: "error",
            });
          }
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getDags() {
      // get list of dag_ids of selected_kaapana_instances
      if (!this.selected_federation_name || this.federated) {
        kaapanaApiService
          .federatedClientApiPost("/get-dags-via-instances", {
            instance_names: this.selected_kaapana_instance_names,
            kind_of_workflows: this.kind_of_workflows,
          })
          .then((response) => {
            this.available_dags = response.data;
          })
          .catch((err) => {
            console.log(err);
          });
      }
      else {
        // ... or via available_federated_permission_profile_ids of selected federation
        console.log("GET DAGS this.available_federated_permission_profile_ids: ", this.available_federated_permission_profile_ids)
        kaapanaApiService
          .federatedClientApiPost("/get-dags-via-fed-perm-profiles", {
            federated_permission_profile_ids: this.available_federated_permission_profile_ids,
            kind_of_workflows: this.kind_of_workflows,
          })
          .then((response) => {
            this.available_dags = response.data;
          })
          .catch((err) => {
            console.log(err);
          });
      }
    },
    getFederations() {
      kaapanaApiService
        .federatedClientApiGet("/federations")
        .then((response) => {
          this.available_federation_names = response.data
            .map(({ federation_name }) => federation_name);
          this.available_federations = response.data;
          console.log("this.available_federations: ", this.available_federations)
        })
        .catch((err) => {
          console.log(err)
        })
    },
    getFederatedPermissionProfiles(federation_id=null, ext_dag_id=null) {
      if (ext_dag_id) {
        kaapanaApiService
          .federatedClientApiGet("/federated-permission-profiles", {
            ext_dag_id
          })
          .then((response) => {
            this.available_federated_permission_profiles = response.data
            this.remote_instances_w_external_dag_available = this.available_federated_permission_profiles.map((fed_perm_profile) => fed_perm_profile.kaapana_instance.instance_name);
          })
          .catch((err) => {
            console.log(err)
          })
        }
      else {
        kaapanaApiService
          .federatedClientApiGet("/federated-permission-profiles", {
            federation_id
          })
          .then((response) => {
            this.available_federated_permission_profiles = response.data
            this.available_federated_permission_profile_ids = response.data
              .map(({ federated_permission_profile_id }) => federated_permission_profile_id);
            console.log("this.available_federated_permission_profile_ids: ", this.available_federated_permission_profile_ids)
          })
          .catch((err) => {
            console.log(err)
          })
        }
    },
    // API Calls: Schemas
    getUiFormSchemas() {
      // remove 'undefined' from instance_names list
      kaapanaApiService
        .federatedClientApiPost("/get-ui-form-schemas", {
          workflow_name: this.workflow_name,
          // instance_names: this.selected_kaapana_instance_names,
          federated_permission_profile_ids: this.selected_federated_permission_profile_ids,
          kind_of_workflows: this.kind_of_workflows,
          only_dag_names: false,
        })
        .then((response) => {
          this.schemas_dict = response.data;
          console.log("GetUIFormSchemas this.schemas_dict: ", this.schemas_dict)
        })
        .catch((err) => {
          console.log(err);
        });
    },
    getExternalUiFormSchemas() {
      kaapanaApiService
        .federatedClientApiPost("/get-ui-form-schemas", {
          workflow_name: this.workflow_name,
          dag_id: this.external_dag_id,
          // instance_names:
          //   this.selected_remote_instances_w_external_dag_available,
          federated_permission_profile_ids: this.selected_federated_permission_profile_ids,
          kind_of_workflows: this.kind_of_workflows,
          only_dag_names: false,
        })
        .then((response) => {
          this.external_schemas = response.data[this.external_dag_id];
        })
        .catch((err) => {
          console.log(err);
        });
    },
    submitWorkflow() {
      // modify attributes remote_data and federated_data depending on instances
      this.federated_data = false;
      if (this.selected_remote_instances_w_external_dag_available.length) {
        this.formData["external_schema_instance_names"] =
          this.selected_remote_instances_w_external_dag_available;
        this.federated_data = true;
      }

      if (this.identifiers.length > 0) {
        this.formData["data_form"] = {
          identifiers: this.identifiers,
        };
      }
      kaapanaApiService
        .federatedClientApiPost("/workflow", {
          workflow_name: this.workflow_name,
          dag_id: this.dag_id,
          instance_names: this.selected_kaapana_instance_names,
          conf_data: this.formatFormData(this.formData),
          remote: this.remote,
          federated: this.federated_data,
          federation_name: this.selected_federation_name,
        })
        .then((response) => {
          console.log(response);
          this.$notify({
            type: "success",
            title: "Workflow successfully created!",
          });
          this.reset();
          if (this.identifiers.length > 0) {
            this.$emit("successful");
          } else {
            this.$router.push({ name: "workflows" });
          }
        })
        .catch((err) => {
          console.log(err);
          this.$notify({
            type: "error",
            title: "An error occured during the workflow creation!",
          });
        });
    },
  },
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">
.is-invalid {
  border: 1px solid red;
}
.justify-space-between {
  justify-content: 0;
}
</style>
