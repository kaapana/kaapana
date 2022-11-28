<template>
  <v-row dense align="center" justify="center">
    <v-col cols="1" />
    <v-col cols="2">
      <v-autocomplete
        solo v-model="key_select" :items="Object.keys(mapping)" :key="key_select"
        dense hide-details
      ></v-autocomplete>
    </v-col>
    <v-col cols="5">
      <v-autocomplete
        :disabled="key_select == null"
        v-model="item_select"
        :items="mapping[key_select] != null ? mapping[key_select]['items'] : null"
        auto-select-first
        chips
        clearable
        deletable-chips
        multiple
        small-chips
        dense
        hide-details
      ></v-autocomplete>
    </v-col>
    <v-col cols="1" align="center">
      <v-btn @click="deleteFilter" small icon>
        <v-icon>mdi-delete</v-icon>
      </v-btn>
    </v-col>
    <v-spacer/>
  </v-row>
</template>

<script>
/* eslint-disable */

import {loadAvailableTags} from "@/common/api.service";

export default {
  name: "SearchItem",
  props: {
    id: {
      type: Number,
    },
    _key_select: {
      type: String
    },
    _item_select: {
      type: Array
    },
    props_change: {
      type: Boolean
    }
  },
  emits: ['deleteFilter'],
  data() {
    return {
      key_select: null,
      item_select: [],
      mapping: {},
      disabled: false,
    }
  },
  mounted() {
    loadAvailableTags()
      .then(res => this.mapping = res.data)

    this.key_select = this._key_select
    this.item_select = this._item_select
  },
  methods: {
    deleteFilter() {
      this.$emit('deleteFilter', this.id)
    }
  },
  watch: {
    _item_select() {
      this.item_select = this._item_select
    },
    _key_select() {
      this.key_select = this._key_select
    },
    key_select() {
      this.item_select = []
    }
  },
  computed: {
    query() {
      if (this.item_select.length > 0) {
        return {
          "bool": {
            "should": this.item_select.map(item => ({
                "match": {
                  [this.mapping[this.key_select]['key']]: item
                }
              })
            )
          }
        }
      } else {
        return null
      }
    }
  }
}
</script>

<style scoped>

</style>
