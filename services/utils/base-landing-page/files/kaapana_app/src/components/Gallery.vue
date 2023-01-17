<template>
  <LazyList
      :data="processed_data"
      :itemsPerRender="24"
      containerClasses="list row"
      defaultLoadingColor="#222"
      style="margin: auto; height:auto"
  >
    <template v-slot="{item}">
      <v-col :cols="cols">
<!--        TODO: maybe provide cohortNames or cache it-->
        <CardSelect
            :cohort_name="cohort_name"
            :cohort_names="cohort_names"
            :series-instance-u-i-d="item.seriesInstanceUID"
            :study-instance-u-i-d="item.studyInstanceUID"
            :selected_tags="inner_selectedTags"
            @imageId="propagateImageId({
                                    seriesInstanceUID: item.seriesInstanceUID,
                                    studyInstanceUID: item.studyInstanceUID,
                                    seriesDescription: item.seriesDescription
                                  })"
            @removeFromCohort="removeFromCohort(item)"
            @deleteFromPlatform="deleteFromPlatform(item)"
        />
      </v-col>
    </template>
  </LazyList>
</template>

<script>
/* eslint-disable */

import Chip from "./Chip.vue";
import LazyList from './lazy-load-list/LazyList.vue'
import CardSelect from "./CardSelect";
import {deleteSeriesFromPlatform, loadCohortNames, updateCohort} from "../common/api.service";

export default {
  name: 'Gallery',
  emits: ['imageId'],
  props: {
    cohort_name: {
      type: String,
      default: null
    },
    data: {
      type: Array
    },
    selectedTags: {
      type: Array
    },
  },
  components: {
    CardSelect,
    Chip,
    LazyList
  },
  data() {
    return {
      cohort_names: [],
      image_id: null,
      inner_data: [],
      inner_selectedTags: []
    };
  },
  mounted() {
    loadCohortNames().then(cohort_names => this.cohort_names = cohort_names)

    this.inner_data = this.data
    this.inner_selectedTags = this.selectedTags
    if (localStorage['Dataset.Gallery.cols'] === undefined) {
      localStorage['Dataset.Gallery.cols'] = JSON.stringify("auto")
    }
  },
  computed: {
    cols() {
      if (JSON.parse(localStorage['Dataset.Gallery.cols']) !== 'auto') {
        return JSON.parse(localStorage['Dataset.Gallery.cols'])
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
    },
    processed_data() {
      return this.inner_data.map(i => {
            return {
              seriesInstanceUID: i['0020000E SeriesInstanceUID_keyword'],
              studyInstanceUID: i['0020000D StudyInstanceUID_keyword'],
              seriesNumber: i['00200011 SeriesNumber_integer'],
              seriesDescription: i['0008103E SeriesDescription_keyword'],
            }
          }
      )
    }
  },
  methods: {
    async removeFromCohort(item) {
      if (this.cohort_name !== null) {
        try {
          await updateCohort({
            "cohort_name": this.cohort_name,
            "action": "DELETE",
            "cohort_query": {"index": "meta-index"},
            "cohort_identifiers": [{"identifier": item.seriesInstanceUID}]
          })
          this.$notify({
            type: 'success',
            text: `Removed series ${item.seriesDescription} from ${this.cohort_name}`
          });
        } catch (error) {
          this.$notify({
            type: 'error',
            title: 'Network/Server error',
            text: error,
          });
        }
      }
      this.removeFromUI(item)
    },
    async deleteFromPlatform(item) {
      try {
        await deleteSeriesFromPlatform(item.seriesInstanceUID)
        this.$notify({
          type: 'success',
          text: `Started deletion of series ${item.seriesDescription}`
        });
      } catch (error) {
        this.$notify({
          type: 'error',
          title: 'Network/Server error',
          text: error,
        });
      }
      this.removeFromUI(item)
    },
    removeFromUI(item) {
      this.inner_data = this.inner_data.filter(
          i => item.seriesInstanceUID !== i['0020000E SeriesInstanceUID_keyword']
      )
      if (this.inner_data.length === 0) {
        this.$emit('emptyStudy')
      }
    },
    propagateImageId(image_id) {
      this.$emit('imageId', image_id);
    },
  },
  watch: {
    data() {
      // TODO: should not be necessary
      this.inner_data = this.data
    },
    selectedTags() {
      this.inner_selectedTags = this.selectedTags
    }
  },
};
</script>
<style scoped>
.col {
  padding: 5px;
}
.inner-gallery-height {
  height: calc(100vh - 78px)
}
</style>
