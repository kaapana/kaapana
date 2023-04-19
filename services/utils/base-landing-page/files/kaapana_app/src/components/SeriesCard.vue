<template>
  <v-container class="pa-0" fluid style="height: 100%">
    <v-card
        @click="onClick"
        height="100%"
        :id="seriesInstanceUID"
    >
      <!--      padding: 5px; background: red-->
      <v-img
          :src="src"
          aspect-ratio="1"
          @error="() => this.img_loading_error = true"
      >
        <template v-slot:placeholder>
          <v-row
              class="fill-height ma-0"
              align="center"
              justify="center"
              :style="img_loading_error ? 'background-color: darkgray': ''"
          >
            <v-progress-circular
                v-if="!img_loading_error"
                indeterminate
                color="#0088cc"
            ></v-progress-circular>
            <div v-else style="text-align: center">
              <p></p>
              <v-icon>mdi-alert-circle-outline</v-icon>
              <p>Thumbnail unavailable</p>
            </div>
          </v-row>
        </template>

        <v-app-bar
            flat
            dense
            color="rgba(0, 0, 0, 0)"
        >
          <Chip :items="[modality]"/>
          <v-spacer></v-spacer>
          <v-btn
              icon
              @click.stop="() => showDetails()"
              color="white"
              >
            <v-icon>mdi-eye-outline</v-icon>
          </v-btn>
        </v-app-bar>
      </v-img>
      <v-card-text v-if="settings.datasets.cardText">
        <v-row no-gutters>
          <v-col cols="11">
            <div class="text-truncate">
              {{ seriesDescription }}
            </div>
          </v-col>
          <v-col cols="1">
            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-icon
                    small
                    v-bind="attrs"
                    v-on="on"
                >
                  mdi-information
                </v-icon>
              </template>
              <v-data-table
                  :headers="[
                    {text: 'Tag', value: 'name'},
                    {text: 'Value', value: 'value'},
                  ]"
                  :items="tagsData"
                  fixed-header
                  :hide-default-footer="true"
                  :items-per-page=-1
                  dense
              />
            </v-tooltip>
          </v-col>
        </v-row>
        <div v-for="prop in settings.datasets.props">
          <div v-if="prop['display']">
            <v-row no-gutters style="font-size: x-small">
              <v-col style="margin-bottom: -5px">
                {{ prop['name'] }}
              </v-col>
            </v-row>
            <v-row no-gutters style="font-size: small; padding-top: 0" align="start">
              <v-col>
                <div :class="prop['truncate'] ? 'text-truncate' : ''">
                  {{ seriesData[prop['name']] || 'N/A' }}
                </div>
              </v-col>
            </v-row>
          </div>
        </div>
        <v-row v-if="tags" no-gutters>
          <TagChip :items="tags" @deleteTag="(tag) => deleteTag(tag)"/>
        </v-row>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
/* eslint-disable */

import Chip from "./Chip.vue";
import TagChip from "./TagChip.vue";

import {loadSeriesData, updateTags} from "@/common/api.service"
import {settings} from "@/static/defaultUIConfig";


export default {
  name: "SeriesCard",
  components: {Chip, TagChip},
  emits: ['openInDetailView'],
  props: {
    seriesInstanceUID: {
      type: String,
    },
    selectedTags: {
      type: Array,
      default: () => ([])
    },
  },
  data() {
    return {
      src: '',
      seriesData: {},
      seriesDescription: '',
      modality: null,
      tags: [],
      settings: settings,
      tagsData: [],

      img_loading_error: false,

      // only required for double-click-event
      clicks: 0,
      timer: null,
    };
  },
  created() {
    this.settings = JSON.parse(localStorage['settings'])
  },
  async mounted() {
    this.get_data();
  },
  watch: {
    // todo: why is this needed?
    async seriesInstanceUID() {
      this.get_data();
    }
  },
  methods: {
    get_data() {
      if (this.seriesInstanceUID !== '') {
        loadSeriesData(this.seriesInstanceUID).then(data => {
          if (data !== undefined) {
            this.src = data['thumbnail_src'] || ''
            this.seriesDescription = data['metadata']['Series Description'] || ''
            this.modality = data['metadata']['Modality'] || ''
            this.seriesData = data['metadata'] || {}
            this.tags = data['metadata']['tags'] || []
            this.tagsData = Object.entries(this.seriesData).map(i => ({name: i[0], value: i[1]}))
          }
        })
      }
    },
    async deleteTag(tag) {
      const request_body = [{
        "series_instance_uid": this.seriesInstanceUID,
        "tags": this.tags,
        "tags2add": [],
        "tags2delete": [tag]
      }]
      updateTags(request_body)
          .then(() => this.tags = this.tags.filter((_tag) => _tag !== tag))
    },
    modifyTags() {
      let request_body = []

      if (this.selectedTags.length === 0) {
        // this.$notify({
        //   type: 'hint',
        //   title: 'No label selected',
        //   text: 'There was no label selected. First select a label and then click on the respective Item to assign it.',
        // })
        return
      }

      const tagsAlreadyExist = this.selectedTags.filter(
          el => this.tags.includes(el)
      ).length === this.selectedTags.length
      if (tagsAlreadyExist) {
        // the selected tags are already included in the tags => removing them
        request_body = [{
          "series_instance_uid": this.seriesInstanceUID,
          "tags": this.tags,
          "tags2add": [],
          "tags2delete": this.selectedTags
        }]
      } else {
        request_body = [{
          "series_instance_uid": this.seriesInstanceUID,
          "tags": this.tags,
          "tags2add": this.selectedTags,
          "tags2delete": []
        }]
      }
      updateTags(request_body)
          .then(() => {
            this.tags =
                tagsAlreadyExist
                    ? this.tags.filter(tag => !this.selectedTags.includes(tag))
                    : Array.from(new Set([...this.tags, ...this.selectedTags]))
          })
    },
    onClick() {
      // helper function
      function single_click() {
        this.timer = setTimeout(() => {
          this.clicks = 0;
          // once the detail view is implemented with improved performance, include the following line again to 
          // open the detail view on a single click
          // this.showDetails()
        }, 300);
      }

      this.clicks++;
      if (this.clicks === 1) {
        return single_click.call(this);
      }

      clearTimeout(this.timer);
      this.clicks = 0;
      // double click
      this.modifyTags()
    },
    showDetails() {
      this.$emit('openInDetailView', this.seriesInstanceUID);
    }
  }
};
</script>

<style scoped>
.selected {
  /*TODO: This should be aligned with theme*/
  color: #fff !important;
  background: #4af !important;
}
</style>
