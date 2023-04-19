<template>
  <v-container fluid style="height: 100%">
  <v-row>
        <v-col v-for="seriesInstanceUID in inner_seriesInstanceUIDs" :key="seriesInstanceUID" :cols="cols">
          <v-lazy 
            :options="{
              threshold: .5,
              delay: 100
            }" 
            transition="fade-transition" class="fill-height" :min-height="400 / cols"
          >
            <SeriesCard 
              :series-instance-u-i-d="seriesInstanceUID"
              :selectedTags="selectedTags" 
              @openInDetailView="openInDetailView(seriesInstanceUID)"
            />
          </v-lazy>
        </v-col>
      </v-row>
  </v-container>
</template>

<script>
/* eslint-disable */

import Chip from "./Chip.vue";
import SeriesCard from "./SeriesCard";
import { deleteSeriesFromPlatform, loadDatasetNames, updateDataset } from "../common/api.service";
import { VueSelecto } from "vue-selecto";

export default {
  name: 'Gallery',
  emits: ['openInDetailView'],
  props: {
    seriesInstanceUIDs: {
      type: Array,
      default: () => []
    },
    selectedTags: {
      type: Array,
      default: () => []
    },
  },
  components: {
    SeriesCard,
    Chip,
    VueSelecto
  },
  data() {
    return {
      detailViewSeriesInstanceUID: null,
      inner_seriesInstanceUIDs: []
    };
  },
  mounted() {
    this.inner_seriesInstanceUIDs = this.seriesInstanceUIDs
  },
  computed: {
    cols() {
      const _cols = JSON.parse(localStorage['settings']).datasets.cols
      if (_cols !== 'auto') {
        return _cols
      } else {
        switch (this.$vuetify.breakpoint.name) {
          case 'xs':
            return 6
          case 'sm':
            return 4
          case 'md':
            return 2
          case 'lg':
            return 2
          case 'xl':
            return 2
        }
      }
    }
  },
  methods: {
    openInDetailView(seriesInstanceUID) {
      this.$emit('openInDetailView', seriesInstanceUID);
    },
  },
  watch: {
    seriesInstanceUIDs() {
      this.inner_seriesInstanceUIDs = this.seriesInstanceUIDs
    },
    selectedTags() {
      console.log(this.selectedTags)
    }
  },
};
</script>
<style scoped>
.col {
  padding: 3px;
}

</style>
