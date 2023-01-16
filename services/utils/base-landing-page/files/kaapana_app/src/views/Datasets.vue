<template>
  <v-container fluid class="content pa-0">
    <v-container fluid class="overview-shared pa-0">
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
            <Search
                :cohort_name=cohort_name
                @search="(query) => updatePatients(query)"
                @saveCohort="(dict) => saveCohort(dict.name, dict.query)"
                @updateCohort="(dict) => updateCohort(dict.name, dict.query)"
            />
          </div>
          <v-divider/>
        </v-card>
      </v-container>
      <v-container fluid class="gallery overflow-auto rounded-0 v-card v-sheet pa-0">
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
      </v-container>
    </v-container>
    <v-container
        fluid class="sidebar rounded-0 v-card v-sheet pa-0"
        :style="this.image_id ? '' : 'height: calc(100vh - 60px);'"
    >
      <DetailView
          v-if="this.image_id"
          :series-instance-u-i-d="this.image_id['seriesInstanceUID']"
          :study-instance-u-i-d="this.image_id['studyInstanceUID']"
          :seriesDescription="this.image_id['seriesDescription']"
          @close="() => this.image_id = null"
      />
      <MetaData
          v-else
          :metaData="this.metadata"
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
import {createCohort, updateCohort, loadCohortNames, loadPatients, loadAvailableTags} from "../common/api.service";
import MetaData from "@/components/MetaData.vue";


export default {
  data() {
    return {
      data: [],
      tags: [],
      image_id: null,
      isLoading: true,
      message: 'Loading...',
      structuredGallery: null,
      cohort_names: [],
      cohort_name: null,
      metadata: {}
    };
  },
  components: {
    DetailView,
    StructuredGallery,
    Search,
    TagBar,
    Gallery,
    MetaData
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

        // update metadata
        this.metadata = (await loadAvailableTags(query)).data
      } catch (e) {
        this.message = e
      } finally {
        this.isLoading = false
      }
    },
    async updateCohort(name, query) {
      try {
        const items = await loadPatients('unstructured', query)
        const body = {
          action: 'UPDATE',
          cohort_name: name,
          cohort_identifiers: items.map(item => ({'identifier': item['0020000E SeriesInstanceUID_keyword']})),
          cohort_query: {index: 'meta-index'}
        }
        await updateCohort(body)
        this.$notify({title: 'Dataset updated', text: `Successfully updated dataset ${name}.`, type: 'success'})
        await this.updatePatients(query)
      } catch (error) {
        this.$notify({title: 'Network/Server error', text: error, type: 'error'});
      }
    },
    async saveCohort(name, query) {
      try {
        const items = await loadPatients('unstructured', query)
        const body = {
          cohort_name: name,
          cohort_identifiers: items.map(item => ({'identifier': item['0020000E SeriesInstanceUID_keyword']})),
          cohort_query: {index: 'meta-index'}
        }
        await createCohort(body)
        this.$notify({title: 'Dataset created', text: `Successfully new dataset ${name}.`, type: 'success'});
        this.cohort_names = await loadCohortNames()
        this.cohort_name = name
        await this.updatePatients(query)
      } catch (error) {
        this.$notify({title: 'Network/Server error', text: error, type: 'error'});
      }
    }
  },
  async created() {
    if (localStorage['Dataset.structuredGallery']) {
      this.structuredGallery = JSON.parse(localStorage['Dataset.structuredGallery'])
    } else {
      this.structuredGallery = false
      localStorage['Dataset.structuredGallery'] = JSON.stringify(this.structuredGallery)
    }
    this.cohort_names = await loadCohortNames()
    // if (
    //     localStorage['Dataset.search.cohort_name']
    //     && this.cohort_names.includes(JSON.parse(localStorage['Dataset.search.cohort_name']))
    // ) {
    //   this.cohort_name = JSON.parse(localStorage['Dataset.search.cohort_name'])
    // }
  }
};
</script>
<style scoped>
.sidebar {
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
