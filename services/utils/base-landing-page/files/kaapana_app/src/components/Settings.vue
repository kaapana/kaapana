<template>
  <div>
    <v-dialog v-model="dialog" width="50vw">
      <template v-slot:activator="{ on, attrs }">
        <v-list-item-title v-bind="attrs" v-on="on">
          Settings
        </v-list-item-title>
      </template>

      <v-card>
        <v-card-title>
          Dataset Configuration
          <v-spacer></v-spacer>
          <v-btn text color="red" @click="restoreDefaultSettings">
            Restore default configuration
          </v-btn>
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col>
              <v-checkbox
                v-model="settings.datasets.cardText"
                label="Show Metadata"
              >
              </v-checkbox>
            </v-col>
            <v-col>
              <v-checkbox
                v-model="settings.datasets.structured"
                label="Structured View"
              >
              </v-checkbox>
            </v-col>
            <v-col>
              <v-select
                v-model="settings.datasets.cols"
                :items="['auto', '1', '2', '3', '4', '6', '12']"
                label="Width of an item in the Dataset view"
              ></v-select>
            </v-col>
          </v-row>
          <v-row>
            <v-col>
              <SettingsTable
                ref="settingsTable"
                :items.sync="settings.datasets.props"
                :structuredView="settings.datasets.structured"
                :showMetaData="settings.datasets.cardText"
              >
              </SettingsTable>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions class="justify-center">
          <v-btn color="primary" @click="onSave"> Save </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import SettingsTable from "@/components/SettingsTable.vue";
import { settings as defaultSettings } from "@/static/defaultUIConfig";

export default {
  data: () => ({
    dialog: false,
    settings: defaultSettings,
    resetConfiguration: false,
  }),
  components: {
    SettingsTable,
  },
  created() {
    this.settings = JSON.parse(localStorage["settings"]);
  },
  methods: {
    restoreDefaultSettings() {
      this.settings = defaultSettings;
    },
    onSave() {
      localStorage["settings"] = JSON.stringify(this.settings);
      this.dialog = false;
      window.location.reload();
    },
  },
};
</script>

<style>
.jsoneditor {
  height: 60vh !important;
}
</style>
