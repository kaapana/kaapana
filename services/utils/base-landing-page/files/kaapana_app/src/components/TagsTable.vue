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
            :hide-default-footer=true
            height="60vh"
            :items-per-page=-1
            dense
        />
      </v-container>
    </v-card>
  </div>
</template>

<script>
/* eslint-disable */
import {getDicomTags} from "../common/api.service";

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
        getDicomTags(this.studyInstanceUID, this.seriesInstanceUID).then(data => this.tagsData = data)
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
