<template>
  <v-menu :offset-x=true :offset-y=false
          transition='scale-transition'
          :close-on-click=true
          :value="openMenu"
  >
    <template v-slot:activator="{ on, attrs }">
      <v-btn
          icon
          v-bind="attrs"
          v-on="on"
          color="white"
      >
        <v-icon>mdi-dots-vertical</v-icon>
      </v-btn>
    </template>
    <v-list>
      <v-list-item
          @click="openInOHIF"
      >
        <v-list-item-title>Open in OHIF Viewer</v-list-item-title>
      </v-list-item>
      <v-list-item
          v-if="cohort_name"
          @click="() => {this.$emit('removeFromCohort')}"
      >
        <v-list-item-title>Remove from cohort</v-list-item-title>
      </v-list-item>
      <v-list-item
          @click="() => {this.$emit('deleteFromPlatform')}"
      >
        <v-list-item-title>Delete from system</v-list-item-title>
      </v-list-item>
      <template>
        <v-menu :offset-x=true :offset-y=false
                transition='scale-transition'
                :close-on-click=true
        >
          <template v-slot:activator="{ on, attrs }">
            <v-list-item v-on="on" @click="openMenu = true">
              Add to Cohort
              <v-spacer></v-spacer>
              <v-icon>mdi-chevron-right</v-icon>
            </v-list-item>
          </template>
          <v-list>
            <v-list-item v-for="cohortName in cohortNames" @click="() => addToCohort(cohortName)">
              <v-list-item-title>{{ cohortName }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </template>
    </v-list>
  </v-menu>
</template>

<script>
/* eslint-disable */

import {loadCohortNames, updateCohort} from "../common/api.service";

export default {
  name: "CardMenu",
  props: {
    cohort_name: {
      type: String,
      default: null
    },
    studyInstanceUID: "",
    seriesInstanceUID: "",
  },
  data() {
    return {
      cohortNames: [],
      openMenu: false
    }
  },
  async mounted() {
    this.cohortNames = await loadCohortNames()
  },
  methods: {
    openInOHIF() {
      window.open(`/ohif/viewer/${this.studyInstanceUID}`)
    },
    async addToCohort(cohortName) {
      // this only works for depth max 1
      this.openMenu = false
      try {
        await updateCohort({
          "cohort_name": cohortName,
          "action": "ADD",
          "cohort_query": {"index": "meta-index"},
          "cohort_identifiers": [{"identifier": this.seriesInstanceUID}]
        })
        this.$notify({
          type: 'success',
          text: `Added ${this.seriesInstanceUID} to dataset ${cohortName}`
        });
      } catch (error) {
        this.$notify({
          type: 'error',
          title: 'Network/Server error',
          text: error,
        });
      }
    }
  }
}
</script>
