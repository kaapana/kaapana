<template>
  <v-card>
    <v-card-title>
      <v-row no-gutters align="center" justify="center">
        <v-col cols="11">
          <div class="text-truncate">
            {{ seriesDescription }}
          </div>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn icon @click="() => this.$emit('close')">
            <v-icon>
              mdi-close
            </v-icon>
          </v-btn>
        </v-col>
      </v-row>
    </v-card-title>
    <v-divider/>
    <v-card-text>
      <CornerStone
          v-if="studyInstanceUID !== '' && seriesInstanceUID !== ''"
          :series-instance-u-i-d="seriesInstanceUID"
          :study-instance-u-i-d="studyInstanceUID"
      />
      <TagsTable
          :series-instance-u-i-d="seriesInstanceUID"
      />
    </v-card-text>
  </v-card>
</template>

<script>
/* eslint-disable */

import TagsTable from './TagsTable.vue';
import CornerStone from "./CornerStone.vue";
import {loadSeriesData} from "../common/api.service";

export default {
  name: 'DetailView',
  components: {
    TagsTable,
    CornerStone
  },
  props: {
    seriesInstanceUID: String
  },
  data() {
    return {
      studyInstanceUID: '',
      seriesDescription: ''
    };
  },
  methods: {
    async getDicomData() {
      if (this.seriesInstanceUID) {
        loadSeriesData(this.seriesInstanceUID).then(data => {
          this.studyInstanceUID = data['metadata']['Study Instance UID'] || ''
          this.seriesDescription = data['metadata']['Series Description'] || ''
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
<style scoped>
.card-text {
  height: 30.5vh;
  float: left;
  overflow-y: scroll;
}
</style>
