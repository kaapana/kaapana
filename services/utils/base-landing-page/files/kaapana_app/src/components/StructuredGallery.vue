<template>
  <LazyList
    :data="inner_patients"
    :itemsPerRender="5"
    containerClasses="list"
    defaultLoadingColor="#222"
  >
    <template v-slot="{item}">
      <v-list>
        <v-list-group v-model="item.active">
          <template v-slot:activator>
            <v-list-item-content>
              <v-row no-gutters>
                <v-col cols="4">
                  {{ item.patient_key }}
                </v-col>
                <v-col cols="3" class="text--secondary">
                  Age: {{ item['00101010 PatientAge_integer'] || 'N/A' }}
                </v-col>
                <v-col cols="2" class="text--secondary">
                  Sex: {{ item['00100040 PatientSex_keyword'] || 'N/A' }}
                </v-col>
                <v-col cols="3">
                  <Chip :items="[...item['modalities']]"/>
                </v-col>
              </v-row>
            </v-list-item-content>
          </template>
          <v-list subheader>
            <v-list-item
              v-for="study in [...item.studies]
              .sort((a, b) =>
                new Date(b['00080020 StudyDate_date']) - new Date(a['00080020 StudyDate_date'])
              )"
              :key="JSON.stringify(study)">

              <v-list-item-content>
                <v-list-item-title>
                  {{ study['00081030 StudyDescription_keyword'] }}
                </v-list-item-title>
                <v-list-item-subtitle> {{
                    study['00080020 StudyDate_date']
                  }}
                </v-list-item-subtitle>
                <v-container fluid style="padding: 10px">
                  <v-row>
                    <Gallery
                      :data="study.series"
                      :selectedTags="inner_selectedTags"
                      :cohort_name="cohort_name"
                      @imageId="(imageId) => propagateImageId(imageId)"
                      @emptyStudy="() => removeEmptyStudy(item, study)"
                    />
                  </v-row>
                </v-container>
              </v-list-item-content>
            </v-list-item>
          </v-list>
        </v-list-group>
      </v-list>
    </template>
  </LazyList>
</template>

<script>
/* eslint-disable */
import Chip from "./Chip";
import CardSelect from "./CardSelect.vue";
import Gallery from "./Gallery.vue";
import LazyList from './lazy-load-list/LazyList.vue'

export default {
  emits: ['imageId'],
  props: {
    cohort_name: {
      type: String,
      default: null
    },
    patients: {
      type: Array
    },
    selectedTags: {
      type: Array
    },
  },
  data() {
    return {
      active: {},
      image_id: null,
      inner_patients: [],
      inner_selectedTags: []
    };
  },
  components: {
    CardSelect,
    Chip,
    LazyList,
    Gallery
  },
  mounted() {
    this.inner_patients = this.patients
    this.inner_patients.forEach(pat => pat.active = true)
    this.inner_selectedTags = this.selectedTags
  },
  watch: {
    patients() {
      // TODO why is this needed?
      this.inner_patients = this.patients
      this.inner_patients.forEach(pat => pat.active = true)
      this.inner_selectedTags = this.selectedTags
    },
    selectedTags() {
      this.inner_selectedTags = this.selectedTags
    }
  },
  methods: {
    propagateImageId(image_id) {
      this.$emit('imageId', image_id);
    },
    removeEmptyStudy(item, study) {
      item.studies = item.studies.filter(s => s.study_key !== study.study_key)
      if (item.studies.length === 0){
        this.inner_patients = this.inner_patients.filter(patient => item.patient_key !== patient.patient_key)
      }
    }
  },
};
</script>
<style>
.v-list {
  padding: 0px;
}
.v-list .v-list-item--active {
  background-color: #E3ECF4; /* TODO: this should be synced with theme */
}

</style>

<style scoped>
.col {
  padding: 5px;
}
</style>
