<template>
  <div>
    <v-card class="rounded-0">
      <v-card-title>
        DICOM Tags
        <v-spacer></v-spacer>
        <v-text-field
          v-model="search"
          append-icon="mdi-magnify"
          label="Search"
          single-line
          hide-details
        ></v-text-field>
      </v-card-title>
      <v-container class="pa-0" fluid>
        <v-data-table
          :headers="headers"
          :items="tagsData"
          :search="search"
          fixed-header
          :hide-default-footer="true"
          height="calc(100vh - 355px)"
          items-per-page=-1
        />
      </v-container>
    </v-card>
  </div>
</template>

<script>
/* eslint-disable */
import {loadMetaData, formatMetadata} from "../common/api.service";

export default {
  name: 'TagsTable',
  props: {
    seriesInstanceUID: {
      type: String,
    },
    studyInstanceUID: {
      type: String,
    },
  },
  data: () => ({
    tagsData: [],
    headers: [
      {text: 'Tag', value: 'name'},
      {text: 'Value', value: 'value'},
    ],
    search: null
  }),
  methods: {
    async getDicomData() {
      if (this.seriesInstanceUID && this.studyInstanceUID) {
        loadMetaData(this.studyInstanceUID, this.seriesInstanceUID).then(data => {
          formatMetadata(JSON.stringify(data[0])).then(data => {
            this.tagsData = data.data
          })
        })

      }
    },
  },
  watch: {
    seriesInstanceUID() {
      this.getDicomData();
    },
  },
  created() {
    this.getDicomData();
  },
};
</script>
