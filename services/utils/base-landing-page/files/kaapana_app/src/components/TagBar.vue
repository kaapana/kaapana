<template>
  <!--  edit Mode-->
  <v-row v-if="editMode" dense align="center" style="padding-top: 5px; padding-bottom: 5px">
    <v-col cols="1" align="center">
      <v-icon>mdi-tag-outline</v-icon>
    </v-col>
    <v-col cols="9">
      <v-combobox
          label="Tags"
          v-model="tags"
          :items="availableTags"
          chips
          clearable
          multiple
          single-line
          append-icon=""
          deletable-chips
          flat
          small-chips
          hide-details
          dense
      >
      </v-combobox>
    </v-col>
    <v-col cols="1" align="center">
      <v-checkbox
          v-model="multiple"
          label="Multiple"
          dense
          hide-details
      ></v-checkbox>
    </v-col>
    <v-col cols="1" align="center">
      <v-btn @click="editMode = !editMode" small icon :disabled="tags.length === 0">
        <v-icon>mdi-content-save</v-icon>
      </v-btn>
    </v-col>
  </v-row>
  <!--  Tagging Mode-->
  <v-row v-else dense align="center">
    <v-col cols="1" align="center">
      <v-icon>mdi-tag-outline</v-icon>
    </v-col>
    <v-col cols="10" align="center">
      <v-chip-group
          v-model="selection"
          active-class="deep-purple--text text--accent-4"
          :multiple="settings.datasets.tagBar.multiple"
          @change="onChangeSelection"
          dense
      >
        <v-chip v-for="tag in tags" :key="tag" small :disabled="!settings.datasets.cardText">
          {{ tag }}
        </v-chip>
      </v-chip-group>
    </v-col>
    <v-col cols="1" align="center">
      <v-btn @click="editMode = !editMode" small icon>
        <v-icon>mdi-application-edit-outline</v-icon>
      </v-btn>
    </v-col>
  </v-row>
</template>

<script>
/* eslint-disable */


import {loadValues} from "@/common/api.service";
import {settings} from "@/static/defaultUIConfig";


export default {
  data() {
    return {
      selection: null,
      editMode: true,
      availableTags: [],
      multiple: settings.datasets.tagBar.multiple,
      tags: settings.datasets.tagBar.tags,
      settings: settings
    };
  },
  emits: ['selectedTags'],
  mounted() {
    this.settings = JSON.parse(localStorage['settings'])
    this.multiple = this.settings.datasets.tagBar.multiple
    this.tags = this.settings.datasets.tagBar.tags

    if (this.settings.datasets.tagBar.tags.length > 0)
      this.editMode = false

    loadValues({}, 'Tags')
        .then(res => this.availableTags = 'tags' in res.data ? res.data['tags']['items'].map(i => i['value']) : [])

    window.addEventListener("keypress", event => this.keypressListener(event));
  },
  beforeDestroy() {
    window.removeEventListener('keypress', event => this.keypressListener(event))
  },
  methods: {
    onChangeSelection(e) {
      if (this.multiple) {
        this.$emit('selectedTags', this.selection.map(i => this.tags[i]))
      } else {
        this.$emit('selectedTags', [this.tags[this.selection]])
      }
    },
    keypressListener(e) {
      const keyCode = String.fromCharCode(e.keyCode)
      if (this.editMode || !Number.isInteger(Number(keyCode)))
        return
      const n = parseInt(keyCode) - 1
      if (n >= 0 && n < this.tags.length) {
        if (this.multiple) {
          if (this.selection.filter(t => t === n).length > 0) {
            // already selected
            this.selection = this.selection.filter(t => t !== n)
          } else {
            // not selected yet -> add to selection
            this.selection.push(n)
          }
          this.$emit('selectedTags', this.selection.map(i => this.tags[i]))
        } else {
          this.selection = n
          this.$emit('selectedTags', [this.tags[this.selection]])
        }
      }
    }
  },
  watch: {
    multiple() {
      if (this.multiple) {
        this.selection = []
      } else {
        this.selection = null
      }
      const settings = JSON.parse(localStorage['settings'])
      settings.datasets.tagBar.multiple = this.multiple
      localStorage['settings'] = JSON.stringify(settings)
    },
    tags() {
      const settings = JSON.parse(localStorage['settings'])
      settings.datasets.tagBar.tags = this.tags
      localStorage['settings'] = JSON.stringify(settings)
    }
  }
};
</script>
<style scoped>
</style>
