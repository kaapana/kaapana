<template>
  <LazyList
    :data="processed_data"
    :itemsPerRender="24"
    containerClasses="list row"
    defaultLoadingColor="#222"
    style="margin: auto;"
  >
    <template v-slot="{item}">
      <v-col :cols="cols">
        <CardSelect
          :series-instance-u-i-d="item.seriesInstanceUID"
          :study-instance-u-i-d="item.studyInstanceUID"
          :selected_tags="inner_selectedTags"
          @imageId="propagateImageId({
                                    seriesInstanceUID: item.seriesInstanceUID,
                                    studyInstanceUID: item.studyInstanceUID,
                                    seriesDescription: item.seriesDescription
                                  })"
          @removeFromCohort="removeFromCohort(item)"
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

export default {
  name: 'Gallery',
  emits: ['imageId'],
  props: {
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
      image_id: null,
      inner_data: [],
      inner_selectedTags: []
    };
  },
  mounted() {
    this.inner_data = this.data
    this.inner_selectedTags = this.selectedTags
    if (localStorage['StructuredGallery.cols'] === undefined) {
      localStorage['StructuredGallery.cols'] = JSON.stringify("auto")
    }
  },
  computed: {
    cols() {
      if (JSON.parse(localStorage['StructuredGallery.cols']) !== 'auto') {
        return JSON.parse(localStorage['StructuredGallery.cols'])
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
    removeFromCohort(item) {
      // TODO server request missing
      this.inner_data = this.inner_data.filter(
        i => item.seriesInstanceUID !== i['0020000E SeriesInstanceUID_keyword']
      )
      if (this.inner_data.length === 0){
        this.$emit('studyDeleted')
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
</style>
