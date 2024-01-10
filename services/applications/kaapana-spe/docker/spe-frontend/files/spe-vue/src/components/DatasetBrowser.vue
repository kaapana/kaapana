<template>
    <v-app>
    <v-card>
    <v-row>
      <v-col cols="6">
        <v-card>
          <v-card-title>First List</v-card-title>
          <v-divider></v-divider>
          <v-list>
            <v-list-item v-for="(item, index) in firstList" 
            :key="index" 
            :value="item" 
            :title="item.name" 
            @click="selectItem(item)">
            </v-list-item>
        </v-list>
        </v-card>
      </v-col>
      
      <v-col cols="6">
          <v-card-title>Details</v-card-title>
          <v-divider></v-divider>
          <v-container v-if="selectedItem">
            <v-row>
              <v-col>
                <v-container>
                    <h2>{{ selectedItem.name }}</h2>
                    <p>{{ selectedItem.description }}</p>
                </v-container>
              </v-col>
            </v-row>
          </v-container>
          <v-container v-else>
            <v-row>
              <v-col>
                <p>No item selected</p>
              </v-col>
            </v-row>
          </v-container>
      </v-col>
    </v-row>
</v-card>
</v-app>
</template>
  
<script>

// import { loadDatasets } from "../services/api.service";
import axios from 'axios';



export default {
    data() {
        return {
            datasets: loadDatasets(),
            selectedItem: null,
        };
    },
    methods: {
        selectItem(item) {
        this.selectedItem = item;
        },
        const loadDatasets = async (namesOnly = true) => {
          try {
            const datasets = await axios.get(
              KAAPANA_BACKEND_ENDPOINT + "client/datasets"
            );
            if (namesOnly) {
              return datasets.data.map((dataset) => dataset.name);
            } else {
              return datasets.data;
            }
          } catch (error) {
            Vue.notify({
              title: "Error",
              text:
                error.response && error.response.data && error.response.data.detail
                  ? error.response.data.detail
                  : error,
              type: "error",
            });
          }
      },
    },
};
</script>  



   <!-- <template>
    <v-app>
      <v-container>
        <v-list>
          <v-list-item title="My Application" subtitle="Vuetify"></v-list-item>
          <v-divider></v-divider>
          <v-list-item link title="List Item 1"></v-list-item>
          <v-list-item link title="List Item 2"></v-list-item>
          <v-list-item link title="List Item 3"></v-list-item>
        </v-list>
      </v-container>
    </v-app>
  </template> -->