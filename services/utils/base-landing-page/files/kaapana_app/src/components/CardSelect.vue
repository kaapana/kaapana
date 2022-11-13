<template>
  <v-container class="pa-0"fluid style="height: 100%">
    <v-card
      @click="onClick"
      height="100%"
    >
      <!--      padding: 5px; background: red-->
      <v-img
        :src="src"
        aspect-ratio="1"
      >
        <template v-slot:placeholder>
          <v-row
            class="fill-height ma-0"
            align="center"
            justify="center"
          >
            <v-progress-circular
              indeterminate
              color="#0088cc"
            ></v-progress-circular>
          </v-row>
        </template>

        <v-app-bar
          flat
          dense
          color="rgba(0, 0, 0, 0)"
        >
          <Chip :items="[modality]"/>
          <v-spacer></v-spacer>
          <v-menu>
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
                @click="() => {this.$emit('removeFromCohort')}"
              >
                <v-list-item-title>Remove from cohort</v-list-item-title>
              </v-list-item>
              <v-list-item
                @click="() => {'TODO: Not implemented yet'}"
              >
                <v-list-item-title>Delete from system</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-app-bar>
      </v-img>
      <v-card-text v-if="config.show_card_text">
        <v-row no-gutters>
          <v-col cols="12">
            {{ seriesDescription }}
          </v-col>
        </v-row>
        <div v-if="seriesData[data['key']]" v-for="data in config.props"
        >
          <v-row no-gutters style="font-size: x-small">
            <v-col style="margin-bottom: -5px">
              {{ data['name'] }}
            </v-col>
          </v-row>
          <v-row no-gutters style="font-size: small; padding-top: 0" align="start">
            <v-col>
              {{ seriesData[data['key']] }}
            </v-col>
          </v-row>
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

import {loadSeriesFromMeta, updateTags} from "@/common/api.service"


export default {
  name: "CardSelect",
  components: {Chip, TagChip},
  props: {
    seriesInstanceUID: {
      type: String,
    },
    studyInstanceUID: {
      type: String,
    },
    selected_tags: {
      type: Array,
      default: []
    },
  },
  data() {
    return {
      src: '',
      seriesData: {},
      seriesDescription: '',
      modality: null,
      tags: [],
      config: {},

      // only required for double-click-event
      clicks: 0,
      timer: null,
    };
  },
  computed: {},
  async mounted() {
    if (localStorage['CardSelect.config']) {
      this.config = JSON.parse(localStorage['CardSelect.config'])
    } else {
      this.config = {
        show_card_text: true,
        props: [
          {name: 'Study Date', key: '00080020 StudyDate_date'},
          {name: 'Manufacturer', key: '00080070 Manufacturer_keyword'}
        ]
      }
      localStorage['CardSelect.config'] = JSON.stringify(this.config)
    }

    await this.get_data();
  },
  watch: {
    // todo: why is this needed?
    async seriesInstanceUID() {
      await this.get_data();
    }
  },
  methods: {
    async get_data() {
      if (this.seriesInstanceUID !== '') {
        const data = await loadSeriesFromMeta(this.seriesInstanceUID)
        if (data !== undefined) {
          this.src = data.src || ''
          this.seriesDescription = data.seriesDescription || ''
          this.modality = data.modality || ''
          this.seriesData = data.seriesData || {}
          this.tags = data.tags || []
        }
      }
    },
    async deleteTag(tag) {
      const request_body = [{
        "series_instance_uid": this.seriesInstanceUID,
        "tags": this.tags,
        "tags2add": [],
        "tags2delete": [tag]
      }]
      updateTags(JSON.stringify(request_body))
        .then(() => this.tags = this.tags.filter((_tag) => _tag !== tag))
    },
    modifyTags() {
      let request_body = []
      const tagsAlreadyExist = this.selected_tags.filter(
        el => this.tags.includes(el)
      ).length === this.selected_tags.length
      if (tagsAlreadyExist) {
        // the selected tags are already included in the tags => removing them
        request_body = [{
          "series_instance_uid": this.seriesInstanceUID,
          "tags": this.tags,
          "tags2add": [],
          "tags2delete": this.selected_tags
        }]
      } else {
        request_body = [{
          "series_instance_uid": this.seriesInstanceUID,
          "tags": this.tags,
          "tags2add": this.selected_tags,
          "tags2delete": []
        }]
      }

      updateTags(JSON.stringify(request_body))
        .then(() => {
          this.tags =
            tagsAlreadyExist
              ? this.tags.filter(tag => !this.selected_tags.includes(tag))
              : Array.from(new Set([...this.tags, ...this.selected_tags]))
        })
    },
    onClick() {
      // this.$emit('delete')
      // helper function
      function single_click() {
        this.timer = setTimeout(() => {
          this.clicks = 0;
          // single click
          this.modifyTags()
        }, 300);
      }

      this.clicks++;
      if (this.clicks === 1) {
        return single_click.call(this);
      }

      clearTimeout(this.timer);
      this.clicks = 0;
      // double click
      this.show_details(this.seriesInstanceUID)
      // TODO: add indicator for selected element
    },
    show_details(objectImage) {
      this.$emit('imageId', objectImage);
    }
  }
};
</script>

<style>
.vue-select-image__thumbnail--selected {
  background: #0088cc !important;
}

.vue-select-image__thumbnail--disabled {
  background: #b9b9b9;
  cursor: not-allowed;
}
</style>
