<template>
  <v-container fluid class="content pa-0">
    <v-container fluid :class="[this.image_id ? 'overview-shared pa-0' : 'overview-full pa-0' ]">
      <v-container class="pa-0" fluid>
        <v-card class="rounded-0">
          <div style="padding: 0 10px 10px 10px">
            <v-select
              v-model="cohort"
              hint="Cohort"
              :items="cohorts"
              item-text="name"
              item-value="identifiers"
              label="Select"
              persistent-hint
              return-object
              single-line
            ></v-select>
            <TagBar @selectedTags="(_tags) => this.tags = _tags"/>
            <Search ref="search" :cohort=cohort @search="(query) => updatePatients(query)"/>
          </div>
          <v-divider/>
        </v-card>
      </v-container>
      <v-container fluid class="gallery overflow-auto rounded-0 v-card v-sheet pa-0">
        <!--        <ErrorBoundary>-->
        <v-skeleton-loader
          v-if="isLoading"
          class="mx-auto"
          type="list-item@20"
        ></v-skeleton-loader>
        <StructuredGallery
          v-else-if="!isLoading && data.length > 0 && structuredGallery"
          :patients="data"
          :selectedTags="tags"
          :cohort="cohort"
          @imageId="(imageId) => this.image_id = imageId"
        />
        <Gallery
          v-else-if="!isLoading && data.length > 0 && !structuredGallery"
          :data="data"
          :selectedTags="tags"
          :cohort="cohort"
          @imageId="(imageId) => this.image_id = imageId"
        />
        <h3 v-else>
          {{ message }}
        </h3>
        <!--        </ErrorBoundary>-->
      </v-container>
    </v-container>
    <v-container fluid v-if="this.image_id" class="detailView--fixed rounded-0 v-card v-sheet pa-0">
      <ErrorBoundary>
        <DetailView
          :series-instance-u-i-d="this.image_id['seriesInstanceUID']"
          :study-instance-u-i-d="this.image_id['studyInstanceUID']"
          :seriesDescription="this.image_id['seriesDescription']"
          @close="() => this.image_id = null"
        />
      </ErrorBoundary>
    </v-container>
  </v-container>
</template>

<script>
/* eslint-disable */

import DetailView from '@/components/DetailView.vue';
import StructuredGallery from "@/components/StructuredGallery.vue";
import Gallery from "@/components/Gallery.vue";
import Search from "@/components/Search.vue";
import TagBar from "@/components/TagBar.vue";
import {loadCohorts, loadPatients} from "@/common/api.service";


export default {
  data() {
    return {
      data: [],
      tags: [],
      image_id: null,
      isLoading: false,
      message: 'No data found.',
      structuredGallery: null,
      cohorts: [],
      cohort: null
    };
  },
  components: {
    DetailView,
    StructuredGallery,
    Search,
    TagBar,
    Gallery,
  },
  methods: {
    async updatePatients(query = "{}") {
      this.isLoading = true
      let url = (this.structuredGallery ? 'structured' : 'unstructured')
      try {
        loadPatients(url, query).then((data) => {
          this.data = data
          if (this.data.length === 0)
            this.message = 'No data found.'
        })
      } catch (e) {
        this.message = e
      }
      this.isLoading = false
    },
  },
  async created() {
    if (localStorage['Cohort.structuredGallery']) {
      this.structuredGallery = JSON.parse(localStorage['Cohort.structuredGallery'])
    } else {
      this.structuredGallery = true
      localStorage['Cohort.structuredGallery'] = JSON.stringify(this.structuredGallery)
    }
    this.cohorts = await loadCohorts()
  },
  async mounted() {
    this.updatePatients();
  }
};
</script>
<style scoped>
.detailView--fixed {
  width: 30vw;
  height: calc(100vh + 127px);
  float: left;
  overflow-y: auto;
}

.overview-shared {
  width: 70vw;
  height: inherit;
  float: left;
}

.overview-full {
  width: 100vw;
  height: inherit;
  float: left;
}

.gallery {
  height: calc(100vh - 82px);
}

.content {
  height: 100%;
  top: 48px;
  overflow: hidden;
}
.container {
  padding: 0;
}
</style>
