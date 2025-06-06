<template>
  <v-container class="pa-0" fluid style="height: 100%">
    <v-card @click="onClick" height="100%" :id="seriesInstanceUID" class="seriesCard">
      <v-img :src="src" aspect-ratio="1" @error="() => (this.img_loading_error = true)">
        <template v-slot:placeholder>
          <v-row class="fill-height ma-0" align="center" justify="center"
            :style="img_loading_error ? 'background-color: darkgray' : ''">
            <v-progress-circular v-if="!img_loading_error" indeterminate color="#0088cc"></v-progress-circular>
            <div v-else style="text-align: center">
              <p></p>
              <v-icon>mdi-alert-circle-outline</v-icon>
              <p>Thumbnail unavailable</p>
            </div>
          </v-row>
        </template>

        <v-row class="fill-height ma-0 pa-0">
          <v-app-bar flat dense color="rgba(0, 0, 0, 0)">
            <Chip :items="[modality]" />
            <v-spacer></v-spacer>
            <v-btn icon @click.stop="() => showDetails()" color="white">
              <v-icon>mdi-eye</v-icon>
            </v-btn>
          </v-app-bar>
          <v-bottom-navigation 
            v-if="Object.keys(validationResults).length > 0"
            absolute height="30" 
            background-color="transparent" 
            horizontal class="result-container"
          >
              <v-btn 
                small class="v-btn--error-rslt pa-0" 
                v-if="'errors' in validationResults && validationResults['errors'] != 0 && isSeriesComplete"
                @click="triggerValidationResultDetails"
              >
                {{ validationResults['errors'] }} <v-icon left class="mr-1" color="error">mdi-close-circle</v-icon>
              </v-btn>
              <v-btn 
                small class="v-btn--error-rslt pa-0" 
                v-if="'warnings' in validationResults && validationResults['warnings'] != 0 && isSeriesComplete"
                @click="triggerValidationResultDetails"
              >
                {{ validationResults['warnings'] }} <v-icon left class="mr-1" color="warning">mdi-alert-circle</v-icon>
              </v-btn>
              <v-btn 
                small class="pa-0" 
                v-if="!isSeriesComplete"
                @click="triggerValidationResultDetails"
              >
                Broken <v-icon left class="mr-1" color="warning">mdi-format-page-break</v-icon>
              </v-btn>
          </v-bottom-navigation>
        </v-row>
      </v-img>
      <v-card-text v-if="settings.datasets.cardText">
        <div v-for="prop in settings.datasets.props.filter((prop) => prop.display)">
          <v-row no-gutters style="font-size: x-small">
            <v-col style="margin-bottom: -5px">
              {{ prop["name"] }}
            </v-col>
          </v-row>
          <v-row no-gutters style="font-size: small; padding-top: 0" align="start">
            <v-col>
              <div :class="prop['truncate'] ? 'text-truncate' : ''">
                {{ seriesData[prop["name"]] || "N/A" }}
              </div>
            </v-col>
          </v-row>
        </div>
        <v-row v-if="tags" no-gutters>
          <TagChip :items="tags" @deleteTag="(tag) => deleteTag(tag)" />
        </v-row>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
import Chip from "./Chip.vue";
import TagChip from "./TagChip.vue";

import { loadSeriesData, updateTags } from "@/common/api.service";
import { settings as defaultSettings } from "@/static/defaultUIConfig";

export default {
  name: "SeriesCard",
  components: { Chip, TagChip },
  props: {
    seriesInstanceUID: {
      type: String,
    },
  },
  data() {
    return {
      src: "",
      seriesData: {},
      validationResults: {},
      modality: null,
      tags: [],
      settings: defaultSettings,
      isSeriesComplete: true,

      img_loading_error: false,

      // only required for double-click-event
      clicks: 0,
      timer: null,
    };
  },
  created() {
    this.settings = JSON.parse(localStorage["settings"]);
  },
  async mounted() {
    this.get_data();
  },
  watch: {
    // todo: why is this needed?
    async seriesInstanceUID() {
      this.get_data();
    },
  },
  methods: {
    get_data() {
      if (this.seriesInstanceUID !== "") {
        loadSeriesData(this.seriesInstanceUID).then((data) => {
          if (data !== undefined) {
            this.src = data["thumbnail_src"] || "";
            this.modality = data["metadata"]["Modality"] || "";
            this.seriesData = data["metadata"] || {};
            this.tags = data["metadata"]["Tags"] || [];
            this.isSeriesComplete = data?.metadata?.["Is Series Complete"] ?? true;
            if (!this.isSeriesComplete) {
              console.log(this.seriesInstanceUID);
            }
            if ("Validation Results" in this.seriesData) {
              this.processValidationResults(this.seriesData["Validation Results"]);
            }
          }
        });
      }
    },
    async deleteTag(tag) {
      const request_body = [
        {
          series_instance_uid: this.seriesInstanceUID,
          tags: this.tags,
          tags2add: [],
          tags2delete: [tag],
        },
      ];
      updateTags(request_body).then(
        () => (this.tags = this.tags.filter((_tag) => _tag !== tag))
      );
    },
    processValidationResults(results) {
      for (let key in results) {
        const key_without_tagid = key.split(" ")[1];
        let [tagname, tagtype] = key_without_tagid.split("_", 2);
        tagname = tagname.toLowerCase();
        tagname = tagname.replace("validation", "");
        let tagvalue = 0;
        if (tagtype == "integer") {
          tagvalue = parseInt(results[key]);
          if(isNaN(tagvalue)) {
            tagvalue = 0;
          }
        } else if (tagtype == "datetime") {
          tagvalue = Date.parse(results[key]);
        }else {
          tagvalue = results[key];
        }
        this.validationResults[tagname] = tagvalue
      }
    },
    modifyTags() {
      let request_body = [];

      const activeTags = this.$store.getters.activeTags;
      if (activeTags.length === 0 || activeTags[0] === undefined) {
        // no tags selected => do nothing
        return;
      }

      const tagsAlreadyExist =
        activeTags.filter((el) => this.tags.includes(el)).length ===
        activeTags.length;
      if (tagsAlreadyExist) {
        // the selected tags are already included in the tags => removing them
        request_body = [
          {
            series_instance_uid: this.seriesInstanceUID,
            tags: this.tags,
            tags2add: [],
            tags2delete: activeTags,
          },
        ];
      } else {
        request_body = [
          {
            series_instance_uid: this.seriesInstanceUID,
            tags: this.tags,
            tags2add: activeTags,
            tags2delete: [],
          },
        ];
      }
      updateTags(request_body).then(() => {
        this.tags = tagsAlreadyExist
          ? this.tags.filter((tag) => !activeTags.includes(tag))
          : Array.from(new Set([...this.tags, ...activeTags]));
      });
    },
    onClick() {
      // helper function
      function single_click() {
        this.timer = setTimeout(() => {
          this.clicks = 0;
          if (
            !(
              !this.settings.datasets.cardText ||
              this.$store.getters.multiSelectKeyPressed ||
              this.$store.getters.selectedItems.length > 1
            )
          ) {
            this.modifyTags();
          }
        }, 300);
      }

      this.clicks++;
      if (this.clicks === 1) {
        return single_click.call(this);
      }

      clearTimeout(this.timer);
      this.clicks = 0;
      // double click
      this.showDetails();
    },
    triggerValidationResultDetails() {
      this.$store.commit("setValidationResultItem", this.seriesInstanceUID);
      this.$store.commit("setShowValidationResults", true);
    },
    showDetails() {
      this.$store.commit("setDetailViewItem", this.seriesInstanceUID);
    },
    showValidationResults() {
      this.$store.commit("setShowValidationResults", true);
    }
  },
};
</script>

<style lang="scss" scoped>
.selected {
  /*TODO: This should be aligned with theme*/
  color: #fff !important;
  background: #4af !important;
}
.v-card__text {
  padding: 8px;
}
.v-btn--error-rslt{
  min-width: 50px !important;
}
.result-container{
  justify-content: right !important;
}
</style>
