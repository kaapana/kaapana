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
                :seriesInstanceUIDs="seriesInstanceUIDs"
                :selectedTags="selectedTags"
                :cohort_name="cohort_name"
                :cohort_names="cohort_names"
                @openInDetailView="(_seriesInstanceUID) => openInDetailView(_seriesInstanceUID)"
                @emptyStudy="() => removeEmptyStudy(patient, studyInstanceUID)"
                @selectedItems="_seriesInstanceUIDs => collectAndPropagateImageIds(studyInstanceUID, _seriesInstanceUIDs)"
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
import CardSelect from "./CardSelect.vue";
import Gallery from "./Gallery.vue";

export default {
  emits: ['openInDetailView', 'update:patients', 'selectedItems'],
  props: {
    cohort_names: {
      type: Array,
      default: () => []
    },
    cohort_name: {
      type: String,
      default: null
    },
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
      detailViewSeriesInstanceUID: null,
      selectedItems: {},
    };
  },
  components: {
    CardSelect,
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
    },
    collectAndPropagateImageIds(study_id, _seriesInstanceUIDs) {
      this.selectedItems[study_id] = _seriesInstanceUIDs
      this.$emit('selectedItems', Object.values(this.selectedItems))
    },
    removeEmptyStudy(patient, study) {
      const patients_copy = {...this.patients}
      delete patients_copy[patient][study]

      if (Object.values(patients_copy[patient]).length === 0) {
        delete patients_copy[patient]
      }

      this.$emit('update:patients', patients_copy)
    },
  },
};
</script>
<style>

</style>
