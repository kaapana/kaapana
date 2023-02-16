<template>
  <v-container>
    <VueSelecto
        dragContainer=".elements"
        :selectableTargets='[".selecto-area .v-card"]'
        :hitRate='0'
        :selectByClick='true'
        :selectFromInside='true'
        :toggleContinueSelect='["shift"]'
        :ratio='0'
        :scrollOptions='scrollOptions'
        @dragStart="onDragStart"
        @select="onSelect"
        @scroll="onScroll"
    ></VueSelecto>
    <div class="elements selecto-area" id="selecto1" ref="scroller">
      <v-row>
        <v-col v-for="item in processed_data" :cols="cols">
          <v-lazy
              v-model="item.isActive"
              :options="{
                threshold: .5,
                delay: 100
            }"
              class="fill-height">
            <CardSelect
                :cohort_name="cohort_name"
                :cohort_names="cohort_names"
                :series-instance-u-i-d="item.seriesInstanceUID"
                :study-instance-u-i-d="item.studyInstanceUID"
                :selected_tags="inner_selectedTags"
                @imageId="propagateImageId({
                                    seriesInstanceUID: item.seriesInstanceUID,
                                    studyInstanceUID: item.studyInstanceUID,
                                    seriesDescription: item.seriesDescription
                                  })"
                @removeFromCohort="removeFromCohort(item)"
                @deleteFromPlatform="deleteFromPlatform(item)"
            />
          </v-lazy>
        </v-col>
      </v-row>
    </div>
  </v-container>
</template>

<script>
/* eslint-disable */

import Chip from "./Chip.vue";
import CardSelect from "./CardSelect";
import {deleteSeriesFromPlatform, loadCohortNames, updateCohort} from "../common/api.service";
import {VueSelecto} from "vue-selecto";

export default {
  name: 'Gallery',
  emits: ['imageId'],
  props: {
    cohort_name: {
      type: String,
      default: null
    },
    data: {
      type: Array
    },
    selectedTags: {
      type: Array
    },
  },
  components: {
    CardSelect,
    Chip,
    VueSelecto
  },
  data() {
    return {
      cohort_names: [],
      image_id: null,
      inner_data: [],
      inner_selectedTags: [],
      scrollOptions: {},
      selected: []
    };
  },
  mounted() {
    loadCohortNames().then(cohort_names => this.cohort_names = cohort_names)

    this.inner_data = this.data
    this.inner_selectedTags = this.selectedTags
    if (localStorage['Dataset.Gallery.cols'] === undefined) {
      localStorage['Dataset.Gallery.cols'] = JSON.stringify("auto")
    }
  },
  computed: {
    cols() {
      if (JSON.parse(localStorage['Dataset.Gallery.cols']) !== 'auto') {
        return JSON.parse(localStorage['Dataset.Gallery.cols'])
      } else {
        switch (this.$vuetify.breakpoint.name) {
          case 'xs':
            return 6
          case 'sm':
            return 4
          case 'md':
            return 2
          case 'lg':
            return 2
          case 'xl':
            return 2
        }
      }
    },
    processed_data() {
      return this.inner_data.map(i => {
            return {
              seriesInstanceUID: i['0020000E SeriesInstanceUID_keyword'],
              studyInstanceUID: i['0020000D StudyInstanceUID_keyword'],
              seriesNumber: i['00200011 SeriesNumber_integer'],
              seriesDescription: i['0008103E SeriesDescription_keyword'],
              active: false
            }
          }
      )
    }
  },
  methods: {
    onDragStart(e) {
      if (e.inputEvent.target.nodeName === "BUTTON") {
        return false;
      }
      return true;
    },
    onSelect(e) {
      e.added.forEach(el => {
        el.classList.add("selected");
      });
      e.removed.forEach(el => {
        el.classList.remove("selected");
      })
      this.$emit('selected', e.selected.map(el=> el.id))
    },
    onScroll(e) {
      this.$refs.scroller.scrollBy(e.direction[0] * 10, e.direction[1] * 10);
    },
    resetScroll() {
      this.$refs.scroller.scrollTo(0, 0);
    },
    async removeFromCohort(item) {
      if (this.cohort_name !== null) {
        try {
          await updateCohort({
            "cohort_name": this.cohort_name,
            "action": "DELETE",
            "cohort_query": {"index": "meta-index"},
            "cohort_identifiers": [{"identifier": item.seriesInstanceUID}]
          })
          this.$notify({
            type: 'success',
            text: `Removed series ${item.seriesDescription} from ${this.cohort_name}`
          });
        } catch (error) {
          this.$notify({
            type: 'error',
            title: 'Network/Server error',
            text: error,
          });
        }
      }
      this.removeFromUI(item)
    },
    async deleteFromPlatform(item) {
      try {
        await deleteSeriesFromPlatform(item.seriesInstanceUID)
        this.$notify({
          type: 'success',
          text: `Started deletion of series ${item.seriesDescription}`
        });
      } catch (error) {
        this.$notify({
          type: 'error',
          title: 'Network/Server error',
          text: error,
        });
      }
      this.removeFromUI(item)
    },
    removeFromUI(item) {
      this.inner_data = this.inner_data.filter(
          i => item.seriesInstanceUID !== i['0020000E SeriesInstanceUID_keyword']
      )
      if (this.inner_data.length === 0) {
        this.$emit('emptyStudy')
      }
    },
    propagateImageId(image_id) {
      this.$emit('imageId', image_id);
    },
  },
  watch: {
    data() {
      // TODO: should not be necessary
      this.inner_data = this.data
    },
    selectedTags() {
      this.inner_selectedTags = this.selectedTags
    }
  },
};
</script>
<style>

.col {
  padding: 5px;
}

.inner-gallery-height {
  height: calc(100vh - 78px)
}

.cube {
  display: inline-block;
  border-radius: 5px;

  margin: 4px;
  /*background: #eee;*/
  --color: #4af;
}

.elements {
  /*margin-top: 40px;*/
  /*border: 2px solid #eee;*/
}

.selecto-area {
  /*padding: 20px;*/
}

#selecto1 .cube {
  transition: all ease 0.2s;
}

.moveable #selecto1 .cube {
  transition: none;
}

.selected {
  /*TODO: This should be aligned with theme*/
  color: #fff !important;
  background: #4af !important;
}

.scroll {
  overflow: auto;
  /*padding-top: 10px;*/
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

.infinite-viewer,
.scroll {
  width: 100%;
  /*height: 300px;*/
  box-sizing: border-box;
}

.infinite-viewer .viewport {
  /*padding-top: 10px;*/
}

.empty.elements {
  border: none;
}

/*custom virtual scroll*/
.wrapper {
  display: flex !important;
  flex-direction: row;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
}


.scroller {
  /*flex: 1;*/
}

.scroller :deep(.hover) img {
  opacity: 0.5;
}

.item {
  height: 50px;
  padding: 6px;
  margin: 6px;
  border: 1px solid #b0b0b0;
  border-radius: 0.25rem;

  flex: 0 1 80px;
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  justify-content: center;
  align-items: center;
}
</style>
