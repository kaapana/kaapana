<template>
  <div>
    <v-dialog v-model="dialog" width="50vw">
      <template v-slot:activator="{ on, attrs }">
        <v-btn 
          block depressed 
          color="primary" class="blue darken-1" 
          title="Settings"
          v-bind="attrs" v-on="on"
        >
          <v-icon>mdi-cog</v-icon>
        </v-btn>
      </template>

      <v-card>
        <v-tabs v-model="selectedTab">
          <v-tab key="dataset">Dataset Configuration</v-tab>
          <v-tab key="dcm-validation">Dicom Validation</v-tab>
        </v-tabs>
        <v-tabs-items v-model="selectedTab">
          <v-tab-item key="dataset" class="tab-container">
            <v-container fluid>
              <v-card-text>
                <v-row>
                  <v-col>
                    <v-checkbox v-model="settings.datasets.cardText" label="Show Metadata">
                    </v-checkbox>
                  </v-col>
                  <v-col>
                    <v-checkbox v-model="settings.datasets.structured" label="Structured View">
                    </v-checkbox>
                  </v-col>
                  <v-col>
                    <v-select v-model="settings.datasets.cols" :items="['auto', '1', '2', '3', '4', '6', '12']"
                      label="Width of an item in the Dataset view"></v-select>
                  </v-col>
                </v-row>
                <v-row>
                  <v-col>
                    <v-select
                      v-model="settings.datasets.itemsPerPagePagination"
                      :items="[50, 100, 200, 500, 1000, 5000, 10000]"
                      label="Items per Page"
                    ></v-select>
                  </v-col>
                  <v-col>
                    <v-autocomplete
                      v-model="selectedSortKey"
                      :items="sortKeys"
                      label="Sort"
                    ></v-autocomplete>
                  </v-col>
                  <v-col>
                    <v-select
                      v-model="settings.datasets.sortDirection"
                      :items="['asc', 'desc']"
                      label="Sort direction"
                    ></v-select>
                  </v-col> 
                  <v-col>
                    <v-checkbox
                      v-model="settings.datasets.executeSlicedSearch"
                      label="Slicing Search"
                    >
                    </v-checkbox>
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
            </v-container>
          </v-tab-item>
          <v-tab-item key="dcm-validation" class="tab-container">
            <v-container fluid>
              <v-card-text>
                <v-row>
                  <v-col cols="4" class="centered-col"></v-col>
                  <v-col cols="8">
                    <v-checkbox v-model="validateDicoms['exit_on_error']" label="Stop workflow execution on Error"
                      hide-details></v-checkbox>
                  </v-col>
                  <v-col cols="4" class="centered-col">
                    <v-subheader>Default Dicom validation Algorithm</v-subheader>
                  </v-col>
                  <v-col cols="8">
                    <v-select v-model="validateDicoms['validator_algorithm']" :items="['dciodvfy', 'dicom-validator']"
                      class="pa-0"></v-select>
                  </v-col>
                  <v-col cols="4" class="centered-col">
                    <v-subheader>Add DICOM tag to ignore</v-subheader>
                  </v-col>
                  <v-col cols="8">
                    <v-text-field v-model="newTag" append-icon="mdi-plus-thick" label="Add a tag"
                      :error-messages="tagError" @click:append="onValidationTagAdd" @keydown.enter="onValidationTagAdd"
                      class="pa-0"></v-text-field>
                  </v-col>
                  <v-col cols="4"></v-col>
                  <v-col cols="8">
                    <v-chip v-for="item in validateDicoms['tags_whitelist']" close outlined color="red" class="mr-2 mb-2"
                      @click:close="() => removeFromValidationWhitelist(item)">
                      {{ item }}
                    </v-chip>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-container>
          </v-tab-item>
        </v-tabs-items>
        <v-card-actions>
          <v-btn text color="red" @click="restoreDefaultSettings">
            Restore default configuration
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="onSave"> Save </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>



<script>
import kaapanaApiService from "@/common/kaapanaApi.service";
import SettingsTable from "@/components/SettingsTable.vue";
import { settings as defaultSettings } from "@/static/defaultUIConfig";
import { loadDicomTagMapping } from "@/common/api.service";

export default {
  data: () => ({
    dialog: false,
    newTag: '',
    settings: {},
    resetConfiguration: false,
    selectedTab: null,
    validateDicoms: {},
    tagError: "",
    selectedSortKey: null,
    sortMapping:{}
  }),
  components: {
    SettingsTable,
  },
  created() {
    this.loadSettings();
    this.loadSortItems();
    // set the validateDicoms settings and ignored tags
    // ensure both workflows and validateDicoms settings are in
    // localstorage settings
    if (!this.settings.hasOwnProperty('workflows')) {
    this.settings['workflows'] = structuredClone(defaultSettings['workflows']);
    }
    this.validateDicoms = this.settings.workflows["validateDicoms"].properties;
  },
  computed: {
    sortKeys() {
      return Object.keys(this.sortMapping);
    },
  },
  methods: {
    loadSettings() {
      // Load settings from localStorage or use defaults if not available
      try {
        const storedSettings = localStorage.getItem("settings");
        this.settings = storedSettings ? JSON.parse(storedSettings) : JSON.parse(JSON.stringify(defaultSettings));
      } catch (error) {
        console.error("Failed to load settings from localStorage:", error);
        this.settings = JSON.parse(JSON.stringify(defaultSettings));
      }
    },
    restoreDefaultSettings() {
      // copy the defaultSettings value instead of get the value by reference
      this.settings = structuredClone(defaultSettings);
      this.validateDicoms = this.settings.workflows["validateDicoms"].properties;
      this.loadSortItems();
      this.storeSettingsInDb();
    },
    onSave() {
      // save validate dicoms update to settings
      this.settings.workflows['validateDicoms'].properties = this.validateDicoms

      localStorage["settings"] = JSON.stringify(this.settings);
      this.dialog = false;

      this.storeSettingsInDb();
    },
    storeSettingsInDb(reload_after = true) {
      let settingsItems = []
      Object.keys(this.settings).forEach(key => {
        let item = {
          'key': key,
          'value': this.settings[key],
        }
        settingsItems.push(item)
      });

      // console.log(settingsItems);

      kaapanaApiService
          .kaapanaApiPut("/settings", settingsItems)
          .then((response) => {
            // console.log(response);
            if (reload_after) {
              window.location.reload();
            }
          })
          .catch((err) => {
            console.log(err);
          });
    },
    /**
     * Validates the user input against valid DICOM tags and returns a processed DICOM tag.
     * 
     * This function checks if the provided tag value is a valid DICOM tag. It removes any
     * whitespace, converts the string to lowercase, and verifies that only allowed characters
     * (0-9, a-f, (, )) are used. If the input is valid, it formats the tag and returns it.
     * If not, it sets an error message and returns the invalid status.
     * 
     * @param {string} tagval - The input DICOM tag value to be validated.
     * @returns {Array} An array where the first element is a boolean indicating if the tag is valid,
     *                  and the second element is the processed or original tag value.
     */
    validateDicomTag(tagval) {
      // Remove all whitespace characters from the input
      tagval = tagval.replace(/\s/g, "");

      // Check for the empty string first
      if (tagval.length == 0) {
        this.tagError = "Dicom Tag can't be empty e.g (00dd,fa99)";
        return [false, tagval]
      }

      // Convert the input to lowercase
      tagval = tagval.toLowerCase();

      // Replace all the HEX indicator 0x
      tagval = tagval.replaceAll('0x', '')

      // Regular expression to check for allowed characters (0-9, a-f, (, ))
      const allowed_chars = /^[0-9a-f,()]*$/

      // Check if the tag contains only allowed characters
      var isValid = allowed_chars.test(tagval);
      if (!isValid) {
        this.tagError = "Allowed characters `0-9a-f,()` e.g (00dd,fa99)";
        return [isValid, tagval];
      }

      // Regular expression to match valid DICOM tag format (4 hex digits, optional comma, 4 hex digits)
      const dicomTagMatcher = /\b\(?([0-9a-f]{4}),?([0-9a-f]{4})\)?\b/;

      // Extract parts of the tag using the regular expression
      var tagParts = dicomTagMatcher.exec(tagval);
      isValid = (tagParts !== null);
      if (!isValid) {
        this.tagError = "Both part of tag should contain 4 valid chars. e.g (00dd,fa99)";
        return [isValid, tagval];
      }

      // Format the tag to the desired DICOM tag format (xxxx,xxxx)
      tagval = `(${tagParts[1]},${tagParts[2]})`

      // Return the validation status and the processed tag value
      return [isValid, tagval]
    },
    onValidationTagAdd(event) {
      if (this.validateDicoms["tags_whitelist"].includes(this.newTag)) {
        this.tagError = "Tag already exists in tags whitelist";
        return
      }

      const [isValid, trimmedTag] = this.validateDicomTag(this.newTag)
      if (!isValid) {
        return
      }

      this.tagError = "";
      this.validateDicoms["tags_whitelist"].push(trimmedTag);
      this.newTag = '';
    },
    removeFromValidationWhitelist(item) {
      var index = this.validateDicoms["tags_whitelist"].indexOf(item);
      if (index !== -1) {
        this.validateDicoms["tags_whitelist"].splice(index, 1);
      }
    },
    loadSortItems() {
      loadDicomTagMapping().then((data) => {
        this.sortMapping = data; 
        this.selectedSortKey = Object.keys(data).find(key => data[key] === this.settings.datasets.sort);
      })
    },
  },
  watch: {
    selectedSortKey(newKey) {
      this.settings.datasets.sort = this.sortMapping[newKey];
      //console.log('selectedSortKey:', this.settings.datasets.sort);
    },
  },
};
</script>

<style lang="scss" scoped>
.col {
  padding-top: 0px;
  padding-bottom: 0px;
  margin: 0px;
}
</style>

<style>
.jsoneditor {
  height: 60vh !important;
}

.tab-container {
  min-height: 550px;
}

.centered-col {
  align-self: center;
}
</style>
