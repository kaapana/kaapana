<template>
  <v-container fluid class="content pa-0" style="padding-top: 10px !important">
    <v-container fluid class="overview-shared pa-0" style="position: relative">
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
                ref="search"
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
            type="list-item@100"
        ></v-skeleton-loader>
        <!--        property patients in two-ways bound -->
        <StructuredGallery
            v-else-if="!isLoading && Object.entries(patients).length > 0 && settings.datasets.structured"
            :patients.sync="patients"
            :selectedTags="tags"
            :cohort_name="cohort_name"
            :cohort_names="cohort_names"
            @openInDetailView="(seriesInstanceUID) => this.detailViewSeriesInstanceUID = seriesInstanceUID"
            @selectedItems="(_seriesInstanceUIDs) => this.selectedSeriesInstanceUIDs = _seriesInstanceUIDs"
        />
        <!--        seriesInstanceUIDs is not bound due to issues with the Gallery embedded in StructuredGallery-->
        <Gallery
            v-else-if="!isLoading && seriesInstanceUIDs.length > 0 && !settings.datasets.structured"
            :seriesInstanceUIDs="seriesInstanceUIDs"
            :selectedTags="tags"
            :cohort_name="cohort_name"
            :cohort_names="cohort_names"
            @openInDetailView="(seriesInstanceUID) => this.detailViewSeriesInstanceUID = seriesInstanceUID"
            @selectedItems="(_seriesInstanceUIDs) => this.selectedSeriesInstanceUIDs = _seriesInstanceUIDs"
        />
        <h3 v-else>
          {{ message }}
        </h3>
      </v-container>
      <v-speed-dial
          v-if="selectedSeriesInstanceUIDs.length > 0"
          v-model="fab"
          bottom
          right
          absolute
          direction="top"
          :open-on-hover="true"
          transition="slide-y-reverse-transition"
          dense
      >
        <template v-slot:activator>
          <v-btn
              v-model="fab"
              color="blue darken-2"
              dark
              fab
          >
            <v-icon v-if="fab">
              mdi-close
            </v-icon>
            <v-icon v-else>
              mdi-file-edit-outline
            </v-icon>
          </v-btn>
        </template>
        <v-btn
            fab
            dark
            small
            color="green"
        >
          <v-icon>mdi-pencil</v-icon>
        </v-btn>
        <v-btn
            fab
            dark
            small
            color="indigo"
        >
          <v-icon>mdi-plus</v-icon>
        </v-btn>
        <v-btn
            fab
            dark
            small
            color="red"
        >
          <v-icon>mdi-delete</v-icon>
        </v-btn>
      </v-speed-dial>
    </v-container>
    <v-container
        fluid class="sidebar rounded-0 v-card v-sheet pa-0"
    >
      <DetailView
          v-if="this.detailViewSeriesInstanceUID"
          :series-instance-u-i-d="this.detailViewSeriesInstanceUID"
          @close="() => this.detailViewSeriesInstanceUID = null"
      />
      <MetaData
          v-else
          :series-instance-u-i-ds="seriesInstanceUIDs"
          @dataPointSelection="d => addFilterToSearch(d)"
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
import {createCohort, updateDataset, loadCohortNames, loadPatients, loadAvailableTags} from "../common/api.service";
import MetaData from "@/components/MetaData.vue";
import {settings} from "@/static/defaultUIConfig";

export default {
  data() {
    return {
      seriesInstanceUIDs: [],
      patients: {},
      tags: [],
      detailViewSeriesInstanceUID: null,
      selectedSeriesInstanceUIDs: [],
      isLoading: true,
      message: 'Loading...',
      settings: settings,
      cohort_names: [],
      cohort_name: null,
      metadata: {},
      fab: false
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
    addFilterToSearch(selectedItem) {
      this.$refs.search.addFilterItem(selectedItem['key'], selectedItem['value'])
    },
    // TODO: rename
    async updatePatients(query = {}) {
      this.isLoading = true

      loadPatients({
        structured: this.settings.datasets.structured,
        query: query
      }).then((data) => {
        // TODO: this is not ideal...
        if (this.settings.datasets.structured) {
          this.patients = data
          this.seriesInstanceUIDs = Object.values(this.patients).map(studies => Object.values(studies)).flat(Infinity)
        } else {
          this.seriesInstanceUIDs = data
        }
        if (this.seriesInstanceUIDs.length === 0)
          this.message = 'No data found.'
        this.isLoading = false
      }).catch(e => {
        this.message = e
        this.isLoading = false
      })
    },
    async updateCohort(name, query) {
      try {
        const items = await loadPatients({
          structured: false,
          query: query
        })
        const body = {
          action: 'UPDATE',
          cohort_name: name,
          cohort_identifiers: items,
          cohort_query: {index: 'meta-index'}
        }
        await updateDataset(body)
        this.$notify({title: 'Dataset updated', text: `Successfully updated dataset ${name}.`, type: 'success'})
        this.updatePatients(query)
      } catch (error) {
        this.$notify({title: 'Network/Server error', text: error, type: 'error'});
      }
    },
    async saveCohort(name, query) {
      try {
        const items = await loadPatients({
          structured: false,
          query: query
        })
        const body = {
          cohort_name: name,
          cohort_identifiers: items,
          cohort_query: {index: 'meta-index'}
        }
        await createCohort(body)
        this.$notify({title: 'Dataset created', text: `Successfully new dataset ${name}.`, type: 'success'});
        loadCohortNames().then(_cohort_names => this.cohort_names = _cohort_names)
        this.cohort_name = name
        await this.updatePatients(query)
      } catch (error) {
        this.$notify({title: 'Network/Server error', text: error, type: 'error'});
      }
    }
  },
  async created() {
    this.settings = JSON.parse(localStorage['settings'])
    // this.cohort_name = JSON.parse(localStorage['Dataset.search.cohort_name'] || '')
    loadCohortNames().then(_cohort_names => this.cohort_names = _cohort_names)
  }
};
</script>
<style scoped>
.sidebar {
  width: 30%;
  height: calc(100vh - 81px);
  float: left;
  overflow-y: auto;
}

.overview-shared {
  width: 70%;
  float: left;
  height: calc(100vh - 81px);
}

.overview-full {
  width: 100%;
  height: inherit;
  float: left;
}

.gallery {
  height: calc(100vh - 227px);
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
