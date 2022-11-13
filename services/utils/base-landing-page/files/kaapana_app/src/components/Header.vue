<template>
  <div>
    <v-app-bar color="primary" dark dense clipped-left app>
      <v-app-bar-nav-icon @click.stop="drawer = !drawer"></v-app-bar-nav-icon>
      <v-toolbar-title>Gallery View</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-switch
        hide-details
        v-model="$vuetify.theme.dark"
      ></v-switch>
      <v-menu
        left
        bottom
      >
        <template v-slot:activator="{ on, attrs }">
          <v-btn
            icon
            v-bind="attrs"
            v-on="on"
          >
            <v-icon>mdi-dots-vertical</v-icon>
          </v-btn>
        </template>

        <v-list>
          <v-list-item>
            <v-dialog
              v-model="dialog"
              width="500"
            >
              <template v-slot:activator="{ on, attrs }">
                <v-list-item-title
                  v-bind="attrs"
                  v-on="on"
                >
                  Configure
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
          </v-list-item>
        </v-list>
      </v-menu>
    </v-app-bar>
    <v-navigation-drawer clipped v-model="drawer" app>
      <v-list dense>
        <v-list-item-group v-model="group" active-class="deep-purple--text text--accent-4">
          <v-list-item>
            <v-list-item-icon>
              <v-icon>mdi-home</v-icon>
            </v-list-item-icon>
            <v-list-item-title>Home</v-list-item-title>
          </v-list-item>

          <v-list-item>
            <v-list-item-icon>
              <v-icon>mdi-account</v-icon>
            </v-list-item-icon>
            <v-list-item-title>Account</v-list-item-title>
          </v-list-item>
        </v-list-item-group>
      </v-list>
    </v-navigation-drawer>
  </div>
</template>

<script>
/* eslint-disable */

import vueJsonEditor from 'vue-json-editor'

export default {
  data: () => ({
    drawer: false,
    group: null,
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
