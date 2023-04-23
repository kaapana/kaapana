
<template lang="pug">
  v-card
    v-card-title Instance name: {{ instance.instance_name }}
      v-spacer
      v-tooltip(v-if="remote" bottom='')
        template(v-slot:activator='{ on, attrs }')
          v-icon(:color="diff_updated" small dark='' v-bind='attrs' v-on='on')
             | mdi-circle
        span Time since last update: green: 5 min, yellow: 1 hour, orange: 5 hours, else red)
    v-card-text
      div Network: {{ instance.protocol }}://{{ instance.host }}:{{ instance.port }}
      div Fernet key: {{ instance.fernet_key }}
      div Token: {{ instance.token }}
      div SSL:
        v-icon(v-if="instance.ssl_check" small color="green") mdi-check-circle
        v-icon(v-if="!instance.ssl_check" small) mdi-close-circle
      div Sync remote jobs: {{ instance.automatic_update }}
        v-icon(v-if="instance.automatic_update" small color="green") mdi-check-circle
        v-icon(v-if="!instance.automatic_update" small) mdi-close-circle
      div Autmoatically execute pending jobs: {{ instance.automatic_job_execution }}
        v-icon(v-if="instance.automatic_job_execution" small color="green") mdi-check-circle
        v-icon(v-if="!instance.automatic_job_execution" small) mdi-close-circle
      div Created: {{ instance.time_created }}
      div Updated: {{ instance.time_updated }}
      div Allowed dags: 
        v-chip(v-for='dag in instance.allowed_dags' small) {{dag}}
        //- span( v-for='dag in instance.allowed_dags') {{dag}} 
      div Allowed datasets: 
        v-chip(v-for='dataset in instance.allowed_datasets' small) {{dataset}}
    v-card-actions
      v-tooltip(bottom)
        template(v-slot:activator="{ on, attrs }")
          v-btn(v-bind="attrs" v-on="on" @click='editInstance()' small icon)
           v-icon(color="secondary" dark) mdi-pencil
        span edit instance
      v-tooltip(bottom)
        template(v-slot:activator="{ on, attrs }")
          v-btn(v-bind="attrs" v-on="on" @click='deleteInstance()' small icon)
           v-icon(color="secondary" dark) mdi-trash-can-outline
        span delete instance
    v-dialog(v-model='dialogDelete' max-width='500px')
      v-card
        v-card-title.text-h5 Are you sure you want to delete this instance. With it all corresponding jobs are deleted?
        v-card-actions
          v-spacer
          v-btn(color='blue darken-1' text='' @click='closeDelete') Cancel
          v-btn(color='blue darken-1' text='' @click='deleteInstanceConfirm') OK
          v-spacer

</template>

<script>

import kaapanaApiService from "@/common/kaapanaApi.service";


export default {
  name: 'KaapanaInstance',
  data: () => ({
    dialogDelete: false,
  }),
  props: {
    instance: {
      type: Object,
      required: true
    },
    remote: {
      type: Boolean,
      required: true
    }
  },
  watch: {
    dialogDelete (val) {
      val || this.closeDelete()
    },
  },
  computed: {
    instance_time_created() {
      return new Date(this.instance.time_created * 1000).toUTCString();
    },
    instance_time_updated() {
      return new Date(this.instance.time_updated * 1000).toUTCString();
    },
    utc_timestamp() {
      return Date.parse(new Date().toUTCString());
    },
    diff_updated() {
      var datetime = Date.parse(new Date(this.instance.time_updated).toUTCString()); // results in datetime=NaN: Date.parse(new Date(this.instance.time_updated * 1000).toUTCString());
      var now = Date.parse(new Date().toUTCString());
      console.log("datetime: ", datetime, "; now: ", now)

      if( isNaN(datetime) )
      {
          return "";
      }
      var diff_in_seconds = (now - datetime) / 1000
      console.log("diff_in_seconds")

      if (diff_in_seconds < (60*5)) {
        console.log("green")
        return 'green'
      } else if (diff_in_seconds < (60*60)) {
        console.log("yellow")
        return 'yellow'
      } else if (diff_in_seconds < (60*60*5)) {
        console.log("orange")
        return 'orange'
      } else {
        console.log("red")
        return 'red'
      }
    }
  },
  methods:{
    closeDelete() {
      this.dialogDelete = false
    },
    editInstance() {
      this.$emit('ei', this.instance)
    },
    deleteInstanceConfirm () {
      let params = {
        kaapana_instance_id: this.instance.id,
      };
      kaapanaApiService
        .federatedClientApiDelete("/kaapana-instance", params)
        .then((response) => {
          this.$emit('refreshView')
          this.closeDelete()
        })
        .catch((err) => {
          console.log(err);
        });
    },
    deleteInstance() {
      this.dialogDelete = true
    },
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">


</style>
