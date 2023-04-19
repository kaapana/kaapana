<template>
  <div>
    <v-list
        v-for="([patient, studyInstanceUIDs]) in Object.entries(patients)"
        :key="patient"
    >
      <h3> {{ patient }}</h3>
      <v-container style="padding-top: 0">
        <v-list
            v-for="([studyInstanceUID, seriesInstanceUIDs]) in Object.entries(studyInstanceUIDs)"
            :key="studyInstanceUID"
        >
          <h4>{{ studyInstanceUID }}</h4>
          <v-lazy
              :options="{
                  threshold: .0,
                  delay: 100
                }"
          >
            <Gallery
                :ref="studyInstanceUID"
                :seriesInstanceUIDs="seriesInstanceUIDs"
                :selectedTags="selectedTags"
                @openInDetailView="(_seriesInstanceUID) => openInDetailView(_seriesInstanceUID)"
            />
          </v-lazy>
        </v-list>
      </v-container>
    </v-list>
  </div>
</template>

<script>
/* eslint-disable */
import Chip from "./Chip";
import SeriesCard from "./SeriesCard.vue";
import Gallery from "./Gallery.vue";

export default {
  emits: ['openInDetailView', 'update:patients', 'selectedItems'],
  props: {
    patients: {
      type: Object,
      default: () => {}
    },
    selectedTags: {
      type: Array
    },
  },
  data() {
    return {
      detailViewSeriesInstanceUID: null
    };
  },
  components: {
    SeriesCard,
    Chip,
    Gallery
  },
  mounted() {
  },
  watch: {
    selectedTags() {
      console.log(this.selectedTags)
    },
  },
  methods: {
    openInDetailView(seriesInstanceUID) {
      this.$emit('openInDetailView', seriesInstanceUID);
    }
  }
};
</script>
<style>

</style>
