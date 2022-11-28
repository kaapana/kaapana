<template>
  <div>
    <v-dialog
        v-model="dialog"
        width="500"
    >
      <template v-slot:activator="{ on, attrs }">
        <v-list-item-title
            v-bind="attrs"
            v-on="on"
        >
          Settings
        </v-list-item-title>
      </template>

      <v-card>
        <v-card-title>
          Configure
        </v-card-title>

        <v-card-text>
          <vue-json-editor
              v-model="json"
              :show-btns="true"
              :expandedOnStart="true"
              @json-save="onSave"
          />
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
/* eslint-disable */

import vueJsonEditor from 'vue-json-editor'

export default {
  data: () => ({
    dialog: false,
    json: {}
  }),
  components: {
    vueJsonEditor
  },
  mounted() {
    this.json = Object.entries(localStorage).map(([k, v]) => ({[k]: JSON.parse(v)}))
  },
  methods: {
    onSave(value) {
      this.json.forEach(item => Object.entries(item).forEach(([key, value]) => localStorage[key] = JSON.stringify(value)))
      this.dialog = false
      window.location.reload();
    }
  },
  watch: {
    dialog() {
      this.json = Object.entries(localStorage).map(([k, v]) => ({[k]: JSON.parse(v)}))
    }
  }
};
</script>

<style>
.jsoneditor {
  height: 60vh !important;
}
</style>
