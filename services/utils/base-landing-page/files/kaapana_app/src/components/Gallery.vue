<template>
  <v-container ref="container" fluid style="height: 100%">
    <v-row>
      <v-col
        v-for="(seriesInstanceUID, index) in seriesInstanceUIDs"
        :key="seriesInstanceUID"
        :cols="cols"
      >
        <v-lazy
          v-if="index !== 0"
          :options="{
            threshold: 0.3,
            delay: 100,
          }"
          transition="fade-transition"
          class="fill-height"
          :min-height="minHeight"
        >
          <SeriesCard
            :seriesInstanceUID="seriesInstanceUID"
          />
        </v-lazy>

        <SeriesCard
          v-else
          ref="seriesCard"
          :seriesInstanceUID="seriesInstanceUID"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
/* eslint-disable */

import Chip from "./Chip.vue";
import SeriesCard from "./SeriesCard";
import {
  loadDatasetNames,
  updateDataset,
} from "../common/api.service";
import ResizeObserver from "resize-observer-polyfill";
import {debounce} from "@/utils/utils.js";

export default {
  name: "Gallery",
  props: {
    seriesInstanceUIDs: {
      type: Array,
      default: () => [],
    },
  },
  components: {
    SeriesCard,
    Chip,
  },
  data() {
    return {
      detailViewSeriesInstanceUID: null,
      ro: null,
      cols: 2,
      minHeight: 100,
    };
  },
  mounted() {
    this.ro = new ResizeObserver(debounce(this.onResize, 100));
    this.ro.observe(this.$refs.container);
    this.$nextTick(() => {
      this.minHeight = this.$refs.seriesCard[0].$el.clientHeight * 0.85;
    });
  },
  beforeDestroy() {
    this.ro.unobserve(this.$refs.container);
  },
  methods: {
    onResize() {
      const _cols = JSON.parse(localStorage["settings"]).datasets.cols;
      if (_cols !== "auto") {
        this.cols = _cols;
      } else {
        const containerWidth = this.$refs.container.offsetWidth;
        if (containerWidth < 500) {
          this.cols = 6;
        } else if (containerWidth < 650) {
          this.cols = 4;
        } else if (containerWidth < 1080) {
          this.cols = 3;
        } else if (containerWidth < 1920) {
          this.cols = 2;
        } else {
          this.cols = 1;
        }
      }
      // Setting the minHeight to allow smooth lazy loading
      this.minHeight = this.$refs.seriesCard[0].$el.clientHeight * 0.85;
    },
  },
};
</script>
<style scoped>
.col {
  padding: 3px;
}
</style>
