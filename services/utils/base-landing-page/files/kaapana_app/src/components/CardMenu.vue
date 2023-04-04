<template>
  <v-menu :offset-x=true :offset-y=false
          transition='scale-transition'
          :close-on-click=true
          :value="openMenu"
  >
    <template v-slot:activator="{ on, attrs }">
      <v-btn
          icon
          v-bind="attrs"
          v-on="on"
          color="white"
      >
        <v-icon>mdi-dots-vertical</v-icon>
      </v-btn>
    </template>
    <v-list>
      <v-list-item
          @click="openInOHIF"
      >
        <v-list-item-title>Open in OHIF Viewer</v-list-item-title>
      </v-list-item>
      <v-list-item
          v-if="datasetName"
          @click="() => {this.$emit('removeFromDataset')}"
      >
        <v-list-item-title>Remove from Dataset</v-list-item-title>
      </v-list-item>
      <v-list-item
          @click="() => {this.$emit('deleteFromPlatform')}"
      >
        <v-list-item-title>Delete from system</v-list-item-title>
      </v-list-item>
      <template v-if="datasetNames.length > 0">
        <v-menu :offset-x=true :offset-y=false
                transition='scale-transition'
                :close-on-click=true
        >
          <template v-slot:activator="{ on, attrs }">
            <v-list-item v-on="on" @click="openMenu = true">
              Add to Dataset
              <v-spacer></v-spacer>
              <v-icon>mdi-chevron-right</v-icon>
            </v-list-item>
          </template>
          <v-list>
            <v-list-item v-for="_datasetName in datasetNames" @click="() => addToDataset(_datasetName)">
              <v-list-item-title>{{ _datasetName }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </template>
    </v-list>
  </v-menu>
</template>

<script>
/* eslint-disable */

import {loadSeriesData, updateDataset} from "../common/api.service";

export default {
  name: "CardMenu",
  emits: ['removeFromDataset'],
  props: {
    datasetName: {
      type: String,
      default: null
    },
    datasetNames: {
      type: Array,
      default: [],
    },
    seriesInstanceUID: "",
  },
  data() {
    return {
      openMenu: false
    }
  },
  methods: {
    openInOHIF() {
      loadSeriesData(this.seriesInstanceUID)
          .then(data => window.open(`/ohif/viewer/${data['metadata']['Study Instance UID']}`))
    },
    async addToDataset(datasetName) {
      // this only works for depth max 1
      this.openMenu = false
      try {
        await updateDataset({
          "name": datasetName,
          "action": "ADD",
          "identifiers": [this.seriesInstanceUID]
        })
        this.$notify({
          type: 'success',
          text: `Added ${this.seriesInstanceUID} to dataset ${datasetName}`
        });
      } catch (error) {
        this.$notify({
          type: 'error',
          title: 'Network/Server error',
          text: error,
        });
      }
    }
  }
}
</script>
