<template>
  <v-container fluid class="content pa-0">
    <v-container fluid :class="[this.image_id ? 'overview-shared pa-0' : 'overview-full pa-0' ]">
      <v-container class="pa-0" fluid>
        <v-card class="rounded-0">
          <div style="padding: 0 10px 10px 10px">
            <TagBar @selectedTags="(_tags) => this.tags = _tags"/>
            <v-row dense align="center" style="padding-bottom: 5px">
              <v-col cols="1" align="center">
                <v-icon>mdi-folder</v-icon>
              </v-col>
              <v-col>
                <v-select
                    v-model="cohort_name"
                    :items="cohort_names"
                    label="Select Dataset"
                    clearable
                    hide-details
                    return-object
                    single-line
                    dense
                    @click:clear="cohort_name=null"
                ></v-select>
              </v-col>
            </v-row>
            <Search :cohort_name=cohort_name @search="(query) => updatePatients(query)"/>
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
            :cohort_name="cohort_name"
            @imageId="(imageId) => this.image_id = imageId"
        />
        <Gallery
            v-else-if="!isLoading && data.length > 0 && !structuredGallery"
            :data="data"
            :selectedTags="tags"
            :cohort_name="cohort_name"
            @imageId="(imageId) => this.image_id = imageId"
        />
        <h3 v-else>
          {{ message }}
        </h3>
        <!--        </ErrorBoundary>-->
      </v-container>
    </v-container>
    <v-container fluid v-if="this.image_id" class="detailView--fixed rounded-0 v-card v-sheet pa-0">
      <!--      <ErrorBoundary>-->
      <DetailView
          :series-instance-u-i-d="this.image_id['seriesInstanceUID']"
          :study-instance-u-i-d="this.image_id['studyInstanceUID']"
          :seriesDescription="this.image_id['seriesDescription']"
          @close="() => this.image_id = null"
      />
      <!--      </ErrorBoundary>-->
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
import {loadCohortNames, loadPatients} from "@/common/api.service";


export default {
  data() {
    return {
      data: [],
      tags: [],
      image_id: null,
      isLoading: false,
      message: 'No data found.',
      structuredGallery: null,
      cohort_names: [],
      cohort_name: null
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
    if (localStorage['Dataset.structuredGallery']) {
      this.structuredGallery = JSON.parse(localStorage['Dataset.structuredGallery'])
    } else {
      this.structuredGallery = false
      localStorage['Dataset.structuredGallery'] = JSON.stringify(this.structuredGallery)
    }
    this.cohort_names = await loadCohortNames()
    if (
        localStorage['Dataset.search.cohort_name']
        && this.cohort_names.includes(JSON.parse(localStorage['Dataset.search.cohort_name']))
    ) {
      this.cohort_name = JSON.parse(localStorage['Dataset.search.cohort_name'])
    }
  }
};
</script>
<style scoped>
.detailView--fixed {
  width: 30%;
  /*height: calc(100vh + 65px);*/
  float: left;
  overflow-y: auto;
}

.overview-shared {
  width: 70%;
  float: left;
  height: calc(100vh - 81px);
  overflow-y: auto;
}

.overview-full {
  width: 100%;
  height: inherit;
  float: left;
}

.gallery {
  height: calc(100vh - 81px);
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
