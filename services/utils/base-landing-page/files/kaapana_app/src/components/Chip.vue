<template>
  <div>
    <v-chip
      v-for="item in this._items"
      :key="item"
      :color="_stringToColour(item)"
      :class="[_items > 1 ? 'multiple-items' : '' ]"
      style="margin-left: 1px; margin-right: 1px"
      x-small
      text-color="white"
    >
      {{ item }}
    </v-chip>
  </div>
</template>

<script>
/* eslint-disable */
import {stringToColour} from "@/utils/utils.js";

export default {
  name: "Chip",
  props: {
    items: {
      type: Array,
      default: []
    }
  },
  mounted() {
  },
  computed: {
    _items() {
      return this.items.sort()
    }
  },
  methods: {
    _stringToColour(str) {
      return stringToColour(str)
    }
  },
  data() {
    return {}
  }
}
</script>

<style scoped>
.multiple-items {
  margin-left: 1px;
  margin-right: 1px
}
</style>
