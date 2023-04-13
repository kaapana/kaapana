<template>
  <v-container fluid style="height: 100%">
  <v-row>
        <v-col v-for="seriesInstanceUID in inner_seriesInstanceUIDs" :key="seriesInstanceUID" :cols="cols">
          <v-lazy :options="{
            threshold: .5,
            delay: 100
          }" transition="fade-transition" class="fill-height" :min-height="50 * cols">
            <CardSelect :datasetName="datasetName" :datasetNames="datasetNames" :series-instance-u-i-d="seriesInstanceUID"
              :selected_tags="selectedTags" @openInDetailView="openInDetailView(seriesInstanceUID)"
              @removeFromDataset="removeFromDataset([seriesInstanceUID])"
              @deleteFromPlatform="deleteFromPlatform([seriesInstanceUID])" />
          </v-lazy>
        </v-col>
      </v-row>
  </v-container>
</template>

<script>
/* eslint-disable */

import Chip from "./Chip.vue";
import CardSelect from "./CardSelect";
import { deleteSeriesFromPlatform, loadDatasetNames, updateDataset } from "../common/api.service";
import { VueSelecto } from "vue-selecto";

export default {
  name: 'Gallery',
  emits: ['openInDetailView', 'emptyStudy'],
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
            return 2
        }
      }
    }
  },
  methods: {
    async removeFromDatasetCall(seriesInstanceUIDs) {
      try {
        await updateDataset({
          "name": this.datasetName,
          "action": "DELETE",
          "identifiers": seriesInstanceUIDs
        })
        const text = seriesInstanceUIDs.length == 1 ? `series ${seriesInstanceUIDs[0]}` : `${seriesInstanceUIDs.length} series`
        this.$notify({
          type: 'success',
          text: `Removed ${text} from ${ this.datasetName }`
        });
        return true
      } catch (error) {
        this.$notify({
          type: 'error',
          title: 'Network/Server error',
          text: error,
        });
        return false
      }
    },
    async removeFromDataset(seriesInstanceUIDs) {
      if (this.datasetName !== null) {
        const successful = await this.removeFromDatasetCall(seriesInstanceUIDs)
        if (successful) {
          // update UI -> remove series card from view
          // seriesInstanceUIDs.forEach(seriesInstanceUID => {
          //   this.removeFromUI(seriesInstanceUID)
          // })
          this.removeFromUI(seriesInstanceUIDs)
        }
      }
    },
    async deleteFromPlatform(seriesInstanceUIDs) {
      try {
        await deleteSeriesFromPlatform(seriesInstanceUIDs)
        const text = seriesInstanceUIDs.length == 1 ? `series ${seriesInstanceUIDs[0]}` : `${seriesInstanceUIDs.length} series`
        this.$notify({
          type: 'success',
          text: `Deleting ${ text }.`
        });
        this.removeFromUI(seriesInstanceUIDs)
      } catch (error) {
        this.$notify({
          type: 'error',
          title: 'Network/Server error',
          text: error,
        });
      }
    },
    removeFromUI(seriesInstanceUIDsToRemove) {
      this.inner_seriesInstanceUIDs = this.inner_seriesInstanceUIDs.filter(
          seriesInstanceUID => !seriesInstanceUIDsToRemove.includes(seriesInstanceUID)
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
