<template>
  <v-card>
    <v-card-title>
      <v-row no-gutters align="center" justify="center">

        <v-col cols="11">

          <div class="text-no-wrap" style="overflow: scroll;
white-space: nowrap; width: 25vw">
            {{ seriesDescription }}
          </div>
        </v-col>
        <v-col cols="1" align="center">
          <v-btn icon @click="$emit('close')">
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
        :series-instance-u-i-d="seriesInstanceUID"
        :study-instance-u-i-d="studyInstanceUID"
      />
      <TagsTable
        :series-instance-u-i-d="seriesInstanceUID"
        :study-instance-u-i-d="studyInstanceUID"
      />
    </v-card-text>
  </v-card>
</template>

<script>
/* eslint-disable */

import TagsTable from './TagsTable.vue';
import CornerStone from "./CornerStone.vue";

export default {
  name: 'DetailView',
  components: {
    TagsTable,
    CornerStone
  },
  props: {
    seriesInstanceUID: String,
    studyInstanceUID: String,
    seriesDescription: String
  },
  data() {
    return {};
  },
  methods: {},
};
</script>
<style scoped>
.card-text {
  height: 30.5vh;
  float: left;
  overflow-y: scroll;
}
</style>
