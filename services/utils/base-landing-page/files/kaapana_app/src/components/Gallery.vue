<template>
  <v-container fluid style="height: 100%">
      <VueSelecto
          dragContainer=".elements"
          :selectableTargets='[".selecto-area .v-card"]'
          :hitRate='0'
          :selectByClick='true'
          :selectFromInside='true'
          :toggleContinueSelect='["shift"]'
          :ratio='0'
          :scrollOptions='scrollOptions'
          @dragStart="onDragStart"
          @select="onSelect"
          @scroll="onScroll"
      ></VueSelecto>
      <v-container fluid class="elements selecto-area" id="selecto1" ref="scroller" style="height: 100%">
        <v-row>
          <v-col
              v-for="seriesInstanceUID in inner_seriesInstanceUIDs"
              :key="seriesInstanceUID"
              :cols="cols"
          >
            <v-lazy
                :options="{
                  threshold: .5,
                  delay: 100
                }"
                transition="fade-transition"
                class="fill-height"
                :min-height="50*cols"
            >
              <CardSelect
                  :datasetName="datasetName"
                  :datasetNames="datasetNames"
                  :series-instance-u-i-d="seriesInstanceUID"
                  :selected_tags="selectedTags"
                  @openInDetailView="openInDetailView(seriesInstanceUID)"
                  @removeFromDataset="removeFromDataset(seriesInstanceUID)"
                  @deleteFromPlatform="deleteFromPlatform(seriesInstanceUID)"
              />
            </v-lazy>
          </v-col>
        </v-row>
      </v-container>
  </v-container>
</template>

<script>
/* eslint-disable */

import Chip from "./Chip.vue";
import CardSelect from "./CardSelect";
import {deleteSeriesFromPlatform, loadDatasetNames, updateDataset} from "../common/api.service";
import {VueSelecto} from "vue-selecto";

export default {
  name: 'Gallery',
  emits: ['selectedItems', 'openInDetailView', 'emptyStudy'],
  props: {
    datasetNames: {
      type: Array,
      default: () => []
    },
    datasetName: {
      type: String,
      default: null
    },
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
    CardSelect,
    Chip,
    VueSelecto
  },
  data() {
    return {
      detailViewSeriesInstanceUID: null,
      scrollOptions: {},
      selected: [],
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
            return 1
        }
      }
    }
  },
  methods: {
    onDragStart(e) {
      if (e.inputEvent.target.nodeName === "BUTTON") {
        return false;
      }
      return true;
    },
    onSelect(e) {
      e.added.forEach(el => {
        el.classList.add("selected");
      });
      e.removed.forEach(el => {
        el.classList.remove("selected");
      })
      this.$emit('selectedItems', e.selected.map(el => el.id))
    },
    onScroll(e) {
      this.$refs.scroller.scrollBy(e.direction[0] * 10, e.direction[1] * 10);
    },
    resetScroll() {
      this.$refs.scroller.scrollTo(0, 0);
    },
    async removeFromDataset(seriesInstanceUID) {
      if (this.datasetName !== null) {
        try {
          await updateDataset({
            "name": this.datasetName,
            "action": "DELETE",
            "identifiers": [seriesInstanceUID]
          })
          this.$notify({
            type: 'success',
            text: `Removed series ${seriesInstanceUID} from ${this.datasetName}`
          });
          this.removeFromUI(seriesInstanceUID)
        } catch (error) {
          this.$notify({
            type: 'error',
            title: 'Network/Server error',
            text: error,
          });
        }
      }
    },
    async deleteFromPlatform(seriesInstanceUID) {
      try {
        await deleteSeriesFromPlatform(seriesInstanceUID)
        this.$notify({
          type: 'success',
          text: `Started deletion of series ${seriesInstanceUID}`
        });
        this.removeFromUI(seriesInstanceUID)
      } catch (error) {
        this.$notify({
          type: 'error',
          title: 'Network/Server error',
          text: error,
        });
      }
    },
    removeFromUI(seriesInstanceUIDToRemove) {
      this.inner_seriesInstanceUIDs = this.inner_seriesInstanceUIDs.filter(
          seriesInstanceUID => seriesInstanceUIDToRemove !== seriesInstanceUID
      )
      if (this.inner_seriesInstanceUIDs.length === 0) {
        // only relevant for structured Gallery View
        this.$emit('emptyStudy')
      }
    },
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
<style>

.col {
  padding: 5px;
}

.elements {
  /*margin-top: 40px;*/
  /*border: 2px solid #eee;*/
}

.selecto-area {
  /*padding: 20px;*/
}

.selected {
  /*TODO: This should be aligned with theme*/
  color: #fff !important;
  background: #4af !important;
}

.empty.elements {
  border: none;
}
</style>
