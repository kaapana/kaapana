<template>
    <div>
      <v-dialog v-model="dialog" width="40vw">
        <template v-slot:activator="{ on, attrs }">
          <v-btn icon v-bind="attrs" v-on="on">
            <v-icon>mdi-information-outline</v-icon>
          </v-btn>
        </template>
  
        <v-card>
            <v-container fluid>
                <v-img
                class="white--text align-end"
                width="200px"
                src="/img/kaapana.e1e4c040.png"
                ></v-img>
                <v-card-text>
                    
                </v-card-text>

            </v-container>
        </v-card>
      </v-dialog>
    </div>
  </template>
  
  
  
  <script>
  import kaapanaApiService from "@/common/kaapanaApi.service";
  import SettingsTable from "@/components/SettingsTable.vue";
  import { settings as defaultSettings } from "@/static/defaultUIConfig";
  import { loadDicomTagMapping } from "@/common/api.service";
  
  export default {
    data: () => ({
      dialog: false,
    }),
    components: {
    },
    created() {
      
    },
    computed: {
      
    },
    methods: {
      
    },
    watch: {
     
    },
  };
  </script>
  
  <style lang="scss" scoped>
 
  </style>
  
  <style>

  </style>
  