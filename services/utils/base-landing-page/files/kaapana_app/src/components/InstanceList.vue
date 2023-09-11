
<template>
  <v-row>
    <div style="width: 100%;">
      <v-data-table 
        :headers="instanceHeaders" 
        :items="instances || []"
        fluid
      >
        <!-- local or remote indicator -->
        <template v-slot:item.remote="{ item }">
          <v-tooltip v-if="!item.remote" bottom=''>
            <template v-slot:activator='{ on, attrs }'>
              <v-icon color="primary" dark='' v-bind='attrs' v-on='on'>
                | mdi-home
              </v-icon>
            </template>
            <span> local Kaapana Instance </span>
          </v-tooltip>
          <v-tooltip v-if="item.remote" bottom=''>
            <template v-slot:activator='{ on, attrs }'>
              <v-icon :color="diff_updated(item)" dark='' v-bind='attrs' v-on='on'>
                | mdi-cloud-braces
              </v-icon>
            </template>
            <span> remote Kaapana Instance -- last update: {{ item.time_updated }} -- time since last update: green: 5 min, yellow: 1 hour, orange: 5 hours, else red </span>
          </v-tooltip>
        </template>
        <!-- Network -->
        <template v-slot:item.host="{ item }">
            {{ item.protocol }}://{{ item.host }}:{{ item.port }}
        </template>
        <!-- SSL check -->
        <template v-slot:item.ssl_check="{ item }">
          <v-icon v-if="item.ssl_check" color="green">
            mdi-check-circle-outline
          </v-icon>
          <v-icon v-if="!item.ssl_check" color="red">
            mdi-close-circle-outline
          </v-icon>
        </template>
        <!-- Actions -->
        <template v-slot:item.actions="{ item }">
          <!-- edit instance -->
          <EditKaapanaInstance
            :kaapana_instance="item"
            @refreshInstancesFromEditing="callEmitRefreshInstancesFromInstanceList()"
            class="mx-4"
          ></EditKaapanaInstance>
          <!-- copy local instance -->
          <v-tooltip v-if="!item.remote" bottom=''>
            <template v-slot:activator='{ on, attrs }'>
              <v-btn v-bind="attrs" v-on="on" @click='copyInstanceDefToClipboard(item)' small icon>
                <v-icon color="primary" dark='' v-bind='attrs' v-on='on'>
                  mdi-content-copy
                </v-icon>
              </v-btn>
            </template>
            <span> Copy Kaapana Instance definition to clipboard </span>
          </v-tooltip>
          <!-- delete remote instance -->
          <v-tooltip v-if="item.remote" bottom=''>
            <template v-slot:activator='{ on, attrs }'>
              <v-btn v-bind="attrs" v-on="on" @click='deleteInstance()' small icon>
                <v-icon color="primary" dark='' v-bind='attrs' v-on='on'>
                  mdi-trash-can-outline
                </v-icon>
              </v-btn>
            </template>
            <span> Delete Remote Kaapana Instance </span>
          </v-tooltip>
          <v-dialog v-model='dialogDelete' max-width='500px'>
            <v-card>
              <v-card-title>
                Are you sure you want to delete this instance. With it all corresponding jobs are deleted?
              </v-card-title>
              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color='primary' text='' @click='closeDelete()'>
                  Cancel
                </v-btn>
                <v-btn color='primary' text='' @click='deleteInstanceConfirm(item)'>
                  OK
                </v-btn>
                <v-spacer></v-spacer>
              </v-card-actions>
            </v-card>
          </v-dialog>
        </template>
      </v-data-table>
    </div>
  </v-row>
</template>
  
<script>

import kaapanaApiService from "@/common/kaapanaApi.service";

import EditKaapanaInstance from "@/components/EditKaapanaInstance.vue";

export default {
  components: {
    EditKaapanaInstance,
  },

  name: 'InstanceList',

  data: () => ({
    instanceHeaders: [
      { text: '', value: 'remote' },
      { text: 'Instance Name', align: 'start', value: 'instance_name' },
      { text: 'Instance ID', value: 'id' },
      { text: 'Network', value: 'host' },
      { text: 'Token', value: 'token' },
      // { text: 'Time Updated', value: 'time_updated' },
      { text: 'Verify SSL', value: 'ssl_check', align: 'center' },
      { text: 'Fernet Key', value: 'fernet_key' },
      { text: 'Actions', value: 'actions', sortable: false, filterable: false, align: 'center' },
    ],
    dialogDelete: false,
  }),

  props: {
    instances: {
      type: Array,
      required: true
    },
  },

  mounted() {
    this.printInstances()
  },

  watch: {
    dialogDelete (val) {
        val || this.closeDelete()
      },
  },

  computed: {
  },

  methods: {
    printInstances() {
      console.log("instances: ", this.instances, "type", typeof this.instances)
    },
    callEmitRefreshInstancesFromInstanceList() {
      // refresh instances
      this.$emit('refreshInstancesFromInstanceList')
    },
    copyInstanceDefToClipboard(item) {
      console.log("COPY to CLipboard: ", item)
      const copyInstance = `{\n \
           "instance_name": "${item.instance_name}",\n \
           "host": "${item.host}",\n \
           "port": "${item.port}",\n \
           "token": "${item.token}",\n \
           "fernet_key": "${item.fernet_key}",\n \
           "ssl_check": ${item.ssl_check}\n \
          }`
      const textarea = document.createElement("textarea");
      textarea.value = copyInstance;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      this.$notify({
        title: `Instance definition copied to clipboard!`,
        type: "success",
      });
    },
    diff_updated(item) {
      var datetime = Date.parse(new Date(item.time_updated).toUTCString());
      var now = Date.parse(new Date().toUTCString());

      if( isNaN(datetime) )
      {
          return "";
      }
      var diff_in_seconds = (now - datetime) / 1000
  
      if (diff_in_seconds < (60*5)) {
        return 'green'
      } else if (diff_in_seconds < (60*60)) {
        return 'yellow'
      } else if (diff_in_seconds < (60*60*5)) {
        return 'orange'
      } else {
        return 'red'
      }
    },
    closeDelete() {
      this.dialogDelete = false
    },
    deleteInstanceConfirm (item) {
      let params = {
        kaapana_instance_id: item.id,
      };
      kaapanaApiService
        .federatedClientApiDelete("/kaapana-instance", params)
        .then((response) => {
          this.$emit('refreshInstancesFromInstanceList')
          this.closeDelete()
        })
        .catch((err) => {
          console.log(err);
        });
    },
    deleteInstance() {
      this.dialogDelete = true
    },

    // API Calls
  }
}
</script>
  
  <!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss"></style>
  