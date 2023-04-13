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
                :datasetName="datasetName"
                :datasetNames="datasetNames"
                @openInDetailView="(_seriesInstanceUID) => openInDetailView(_seriesInstanceUID)"
                @emptyStudy="() => removeEmptyStudy(patient, studyInstanceUID)"
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
    datasetNames: {
      type: Array,
      default: () => []
    },
    datasetName: {
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
      detailViewSeriesInstanceUID: null
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
    async removeFromDataset(seriesInstanceUIDs) {
      if (this.datasetName === null) {
        return
      }
      const studyInstanceUIDs = (Object.values(this.patients).map(studyInstanceUID=>Object.keys(studyInstanceUID))).flat()
       const successful = await this.$refs[studyInstanceUIDs[0]][0].removeFromDatasetCall(seriesInstanceUIDs)
      if (successful) {
        studyInstanceUIDs.forEach(studyInstanceUID => {
          if (this.$refs[studyInstanceUID]) {
            this.$refs[studyInstanceUID][0].removeFromUI(seriesInstanceUIDs)
          }
      })
      }
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
