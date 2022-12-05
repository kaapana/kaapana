<template>
  <div>
    <v-chip
      v-for="item in _items"
      :key="item"
      :color="_stringToColour(item)"
      style="margin-left: 1px; margin-right: 1px"
      x-small
      close
      @click:close="$emit('deleteTag', item)"
      text-color="white"
    >
      {{ item }}
    </v-chip>
  </div>
</template>

<script>
/* eslint-disable */
import {stringToColour} from "@/utils/utils";

export default {
  name: "TagChip",
  emits: ['deleteTag'],
  props: {
    items: {
      type: Array,
      default: []
    }
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

</style>
