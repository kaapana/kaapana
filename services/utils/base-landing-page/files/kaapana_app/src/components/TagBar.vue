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
          :multiple="this.multiple"
          @change="onChangeSelection"
          dense
      >
        <v-chip v-for="tag in tags" :key="tag" small>
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


import {loadAvailableTags} from "@/common/api.service";


export default {
  data() {
    return {
      tags: [],
      selection: null,
      editMode: true,
      multiple: false,
      availableTags: []
    };
  },
  emits: ['selectedTags'],
  mounted() {
    if (localStorage['Dataset.tagbar.multiple']) {
      this.multiple = JSON.parse(localStorage['Dataset.tagbar.multiple'])
    }

    if (localStorage['Dataset.tagbar.tags']) {
      this.tags = JSON.parse(localStorage['Dataset.tagbar.tags'])
      this.editMode = false
    }

    loadAvailableTags()
        .then(res => this.availableTags = 'dataset tags' in res.data ? res.data['dataset tags']['items'].map(i => i['value']) : [])

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
        console.log(this.multiple)
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
      localStorage['Dataset.tagbar.multiple'] = this.multiple
    },
    tags() {
      localStorage['Dataset.tagbar.tags'] = JSON.stringify(this.tags)
    }
  }
};
</script>
<style scoped>
</style>
