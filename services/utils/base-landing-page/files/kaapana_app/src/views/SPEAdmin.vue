<template lang="pug">
  v-card
    v-card-title
      v-row(align="center")
        v-col(cols=9)
          p User Requests
    
    <v-card-actions class="configure-button">
      <v-btn @click="showConfigDialog">Platform Config</v-btn>
    </v-card-actions>
      <v-dialog v-model="configDialog" max-width="500px">
        <v-card>
          <v-card-title>
            Configuration
          </v-card-title>
          <v-card-text>
            //- <!-- Your configuration form goes here -->
            <v-text-field label="Username" v-model="config.username"></v-text-field>
            <v-text-field label="Password" v-model="config.password"></v-text-field>
            <v-text-field label="User domain" v-model="config.os_user_domain"></v-text-field>
            <v-text-field label="Project name" v-model="config.os_project_name"></v-text-field>
            <v-text-field label="Project ID" v-model="config.os_project_id"></v-text-field>
            <v-text-field label="Network ID" v-model="config.os_network_id"></v-text-field>
            <v-text-field label="Floating IP ools" v-model="config.os_floating_ip_pools"></v-text-field>
            <v-text-field label="Auth URL" v-model="config.os_auth_url"></v-text-field>
            <v-text-field label="SSH key path" v-model="config.ssh_key_path"></v-text-field>
            <v-text-field label="SSH key name" v-model="config.ssh_key_name"></v-text-field>
            <v-text-field label="Image" v-model="config.os_image"></v-text-field>
            <v-text-field label="Volume size" v-model="config.os_volume_size"></v-text-field>
            <v-text-field label="Instance flavor" v-model="config.os_instance_flavor"></v-text-field>
            <v-text-field label="Remote username" v-model="config.remote_username"></v-text-field>
            <v-text-field label="Security groups" v-model="config.os_security_groups"></v-text-field>
            //- <!-- Add more fields as needed -->
          </v-card-text>
          <v-card-actions>
            <v-btn @click="saveConfig">Save</v-btn>
            <v-btn @click="closeConfigDialog">Close</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    
    <v-btn @click="toggleJsonDisplay">{{ showJsonData ? 'Hide Request' : 'Show Request' }}</v-btn>
    <v-btn @click="accept_spe_request">Accept</v-btn>
    <v-btn @click="reject_spe_request">Reject</v-btn>
    v-card-text  
      <div v-if="showJsonData && userRequestData">
        <pre>{{ JSON.stringify(userRequestData, null, 2) }}</pre>
      </div>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";
import { mapGetters } from "vuex";

export default {
  data: () => ({
    dagList: null,
    showJsonData: false,
    userRequestData: null,
    configDialog: false, // Added to control the dialog visibility
    config: {
      username: "",
      password: "",
      os_user_domain: "",
      os_project_name: "",
      os_project_id: "",
      os_network_id: "",
      os_floating_ip_pools: "",
      os_auth_url: "",
      ssh_key_path: "",
      ssh_key_name: "",
      os_image: "",
      os_volume_size: "",
      os_instance_flavor: "",
      remote_username: "",
      os_security_groups: ""
    }
  }),
  computed: {
    ...mapGetters(["currentUser", "isAuthenticated"])
  },
  props: {
    onlyLocal: {
      type: Boolean,
      default: false,
    },
  },
  watch: {
    // watcher for instances
    available_kaapana_instance_names(value) {
      this.selected_kaapana_instance_names = [value[0]];
    },
    selected_kaapana_instance_names(value) {
      if (value.length === 0) {
        this.selected_kaapana_instance_names = [
          this.available_kaapana_instance_names[0],
        ];
      }
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
  },
  methods: {
    initialState() {
      return {
        // instances
        localKaapanaInstance: {},
        available_kaapana_instance_names: [],
        selected_kaapana_instance_names: [],
        selected_remote_instances_w_external_dag_available: [],
        remote_instances_w_external_dag_available: [],
        // DAGs
        dag_id: null,
      };
    },
    showConfigDialog() {
      // Reset the configuration before showing the dialog
      this.config = {
        username: "",
        password: "",
        os_user_domain: "",
        os_project_name: "",
        os_project_id: "",
        os_network_id: "",
        os_floating_ip_pools: "",
        os_auth_url: "",
        ssh_key_path: "",
        ssh_key_name: "",
        os_image: "",
        os_volume_size: "",
        os_instance_flavor: "",
        remote_username: "",
        os_security_groups: "",
      };
      this.configDialog = true; // Show the dialog
    },
    saveConfig() {
      // Handle saving the configuration here
      // You can access the configuration values in this.config
      console.log("Configuration saved", this.config);

      // Close the dialog after saving
      this.configDialog = false;
    },
    closeConfigDialog() {
      // Close the dialog without saving
      this.configDialog = false;
    },
    toggleJsonDisplay() {
      this.showJsonData = !this.showJsonData;
      if (this.showJsonData && !this.userRequestData) {
        // Fetch requestData
        const sampleRequest = {
          "Request": {
            "User ID": 123456789,
            "Origin": "Charite Berlin",
            "Purpose": "Brain Tumour Segmentation Algorithm Development",
            "Requested Dataset": {
              "Name": "Brain Tumour Segmentation",
              "Requested selection": {
                "Size": "10GB",
                "Number of images": "300"
              }
            }
          }
        };
        this.userRequestData = sampleRequest;
      }
    },
    getKaapanaInstances() {
      kaapanaApiService
        .federatedClientApiPost("/get-kaapana-instances")
        .then((response) => {
          this.available_kaapana_instance_names = response.data
            .filter((instance) => {
              if (this.onlyLocal) {
                return !instance.remote;
              }
              return instance.allowed_dags.length !== 0 || !instance.remote;
            })
            .map(({ instance_name }) => instance_name);

          this.localKaapanaInstance = response.data
            .filter((instance) => {
              return !instance.remote;
            })
            .map(({ instance_name }) => instance_name)[0];
        })
        .catch((err) => {
          console.log(err);
        });
    },
    accept_spe_request() {
      // Trigger a dag that would spin up SPE and send link to user
      kaapanaApiService
        .federatedClientApiPost("/workflow", {
          workflow_name: "dag-tfda-spe-orchestrator",
          dag_id: "dag-tfda-spe-orchestrator",
          instance_names: this.selected_kaapana_instance_names,
          conf_data: { "default_platform": {
                         "shell_workflow": "openstack",
                         "container_workflow": "openstack"
                       },
                       "platforms": {
                         "openstack": {
                           "default_flavor": {
                             "shell_workflow": "flavor_1",
                             "container_workflow": "flavor_1"
                           },
                           "platform_flavors": {
                             "flavor_1": {
                               "username": "",
                               "password": "",
                               "os_user_domain": "",
                               "os_project_name": "",
                               "os_project_id": "",
                               "os_network_id": "",
                               "os_floating_ip_pools": "",
                               "os_auth_url": "",
                               "ssh_key_path": "",
                               "ssh_key_name": "",
                               "os_image": "",
                               "os_volume_size": "",
                               "os_instance_flavor": "",
                               "remote_username": "",
                               "os_security_groups": ""
        }}}}},
          remote: false,
          federated: false,
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
      console.log('Accepted');
    },
    reject_spe_request() {
      // Send rejection of request to the User
      console.log('Rejected');
    }
  }
}
</script>

<style>
.configure-button {
  position: absolute;
  top: 0;
  right: 0;
}
button {
  padding: 10px 20px;
  margin: 5px;
}
</style>
