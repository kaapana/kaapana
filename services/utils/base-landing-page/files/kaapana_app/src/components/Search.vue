<template>
  <div>
    <v-row dense align="center">
      <v-col cols="1" align="center">
        <v-icon>mdi-magnify</v-icon>
      </v-col>
      <v-col cols="6">
        <v-text-field
          label="Search"
          v-model="query_string"
          dense
          single-line
          clearable
          hide-details
          @keydown.enter="search"
        />
      </v-col>
      <v-col cols="1" align="center">
        <v-btn @click="addEmptyFilter" icon>
          <v-icon> mdi-filter-plus-outline </v-icon>
        </v-btn>
      </v-col>
      <v-col cols="1" align="center">
        <v-btn
          v-if="!display_filters && filters.length > 0"
          @click="display_filters = !display_filters"
          icon
        >
          <v-icon> mdi-filter-menu </v-icon>
          ({{ filters.length }})
        </v-btn>
        <v-btn
          v-if="display_filters && filters.length > 0"
          @click="display_filters = !display_filters"
          icon
        >
          <v-icon> mdi-filter-menu-outline </v-icon>
          ({{ filters.length }})
        </v-btn>
      </v-col>

      <!-- Copy query button -->
      <v-col cols="1" align="center">
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn icon v-bind="attrs" v-on="on" @click="copyQueryToClipboard">
              <v-icon>mdi-content-copy</v-icon>
            </v-btn>
          </template>
          <span>Copy Query URL to Clipboard</span>
        </v-tooltip>
      </v-col>
      <v-col cols="2" align="center">
        <v-btn color="primary" style="width: 100%" @click="search">
          Search
        </v-btn>
      </v-col>
    </v-row>
    <div v-show="display_filters" v-for="filter in filters" :key="filter.id">
      <v-row dense align="center" justify="center">
        <v-col cols="1" />
        <v-col cols="2">
          <v-autocomplete
            v-model="filter.key_select"
            :items="fieldNames"
            :key="filter.key_select"
            dense
            hide-details
            @change="updateMapping(filter)"
          ></v-autocomplete>
        </v-col>
        <v-col cols="5">
          <v-autocomplete
            :disabled="filter.key_select == null"
            v-model="filter.item_select"
            :items="
              mapping[filter.key_select] != null
                ? mapping[filter.key_select]['items']
                : null
            "
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
          <v-btn @click="deleteFilter(filter.id)" small icon>
            <v-icon>mdi-delete</v-icon>
          </v-btn>
        </v-col>
        <v-spacer />
      </v-row>
    </div>
  </div>
</template>

<script>
import {
  loadDatasets,
  loadDatasetByName,
  loadFieldNames,
  loadValues,
} from "../common/api.service";
import SaveDatasetDialog from "@/components/SaveDatasetDialog.vue";
import { mapGetters } from "vuex";

export default {
  name: "Search",
  props: {
    datasetName: null,
  },
  data() {
    return {
      datasetNameLocal: this.datasetName,
      query_string: "",
      display_filters: true,
      filters: [],
      counter: 0,
      fieldNames: [],
      mapping: {},
      dialog: false,
      queryParams: this.$route.query,
    };
  },
  components: { SaveDatasetDialog },
  computed: {
    ...mapGetters(["selectedProject"]),
  },
  methods: {
    async addFilterItem(key, value) {
      // check if mapping yet empty, if so, initialize it
      if (Object.keys(this.mapping).length === 0) {
        await this.initializeMapping();
      }

      // check if key actually exists in mapping, if not, raise an error
      if (!this.mapping[key]) {
        this.$notify({
          title: "Error",
          text: `Key ${key} does not exist.`,
          type: "error",
        });
        return;
      }
      // check if the filter already exists
      const filters = this.filters.filter(
        (filter) => filter.key_select === key
      );
      if (
        filters.length > 0 &&
        filters[0].item_select.filter((item) => String(item) === String(value))
          .length === 0
      ) {
        filters[0].item_select.push(
          this.mapping[key]["key"].endsWith("_integer") ||
            this.mapping[key]["key"].endsWith("_float")
            ? parseFloat(value)
            : value
        );
      } else if (filters.length === 0) {
        const res = await loadValues(key, this.constructDatasetQuery() || {});
        this.mapping[key] = res.data;
        // if key ends with '_integer' or '_float' parse the values as numbers
        this.filters.push({
          id: this.counter++,
          key_select: key,
          item_select:
            this.mapping[key]["key"].endsWith("_integer") ||
            this.mapping[key]["key"].endsWith("_float")
              ? [parseFloat(value)]
              : [value],
        });
      }
      this.display_filters = true;
    },
    addEmptyFilter() {
      this.display_filters = true;
      this.filters.push({
        id: this.counter++,
      });
    },
    deleteFilter(id) {
      this.filters = this.filters.filter((filter) => filter.id !== id);
    },
    async composeQuery() {
      const query = {
        bool: {
          must: [
            this.constructDatasetQuery() || "",
            ...this.filters
              .map((filter) => this.queryFromFilter(filter))
              .filter((query) => query !== null),
            {
              query_string: {
                query: this.query_string || "*",
              },
            },
          ],
        },
      };
      return query;
    },
    async search() {
      this.$emit("search", await this.composeQuery());
    },
    queryFromFilter(filter) {
      if (filter.item_select && filter.item_select.length > 0) {
        return {
          bool: {
            should: filter.item_select.map((item) => ({
              match: {
                [this.mapping[filter.key_select]["key"]]: item,
              },
            })),
          },
        };
      } else {
        return null;
      }
    },
    constructDatasetQuery() {
      if (this.dataset && this.dataset.identifiers) {
        return {
          ids: {
            values: this.dataset.identifiers,
          },
        };
      } else {
        return null;
      }
    },
    async updateMapping(filter) {
      filter.item_select = [];
      const key = filter.key_select;
      const res = await loadValues(key, this.constructDatasetQuery() || {});
      this.mapping[key] = res.data;
    },
    async reloadDataset() {
      this.dataset =
        this.datasetNameLocal &&
        (await loadDatasetByName(this.datasetNameLocal));
    },

    /**
     * Processes the query parameters provided via the URL. 
     * Extracts the dataset name and other DICOM query filters from the URL and sets them as filter for the search. 
     * Afterwards the search is executed and the URL parameters removed.
     */
    async processQueryParams() {
      if (this.queryParams.dataset_name) {
        const datasetNames = await loadDatasets();
        if (datasetNames.includes(this.queryParams.dataset_name)) {
          this.datasetNameLocal = this.queryParams.dataset_name;
          await this.initSearch();
        }
        // invalid dataset name will be handled in Datasets.vue
      } else {
        await this.initSearch();
      }
      if (this.queryParams.query_string) {
        // set query_string in search component
        this.query_string = decodeURIComponent(this.queryParams.query_string);
      }

      if (this.queryParams) {
        // all other queryparams are filters and should be added as filters
        const params = Object.entries(this.queryParams).filter(
          ([key, value]) =>
            key !== "query_string" &&
            key !== "dataset_name" &&
            key !== "project_name"
        );

        // setting the filters in the search component
        for (let [_key, _value] of params) {
          // encode key and value
          _key = decodeURIComponent(_key);
          _value = decodeURIComponent(_value);
          // if value contains a comma: split it and add multiple filters
          if (_value.includes(",")) {
            for (let val of _value.split(",")) {
              await this.addFilterItem(_key, val);
            }
          } else {
            await this.addFilterItem(_key, _value);
          }
        }
      }
      // if queryparams are present, run search manually
      if (Object.keys(this.queryParams).length > 0) {
        this.search();
        // Remove query parameters from the URL without reloading the page
        window.history.replaceState(
          null,
          "",
          window.location.origin + window.location.pathname
        );
      }
    },

    async initializeMapping() {
      const res = await loadFieldNames();
      this.fieldNames = res.data;
      this.mapping = Object.assign(
        {},
        ...this.fieldNames.map((_name) => ({
          [_name]: { items: [], key: "" },
        }))
      );
    },

    async initSearch() {
      this.filters = [];
      this.dataset =
        this.datasetNameLocal &&
        (await loadDatasetByName(this.datasetNameLocal));
      // not sure if the awaits are necessary
      await this.search();
      await this.initializeMapping();
    },

    assembleQueryUrl() {
      const baseUrl = window.location.origin + window.location.pathname;
      // get current project name from store

      const params = new URLSearchParams();
      if (this.query_string) {
        params.append("query_string", this.query_string);
      }
      if (this.selectedProject && this.selectedProject.name) {
        params.append("project_name", this.selectedProject.name);
      }
      // datasetname
      if (this.datasetNameLocal) {
        params.append("dataset_name", this.datasetNameLocal);
      }
      this.filters.forEach((filter, index) => {
        if (filter.key_select && filter.item_select.length > 0) {
          params.append(filter.key_select, filter.item_select.join(","));
        }
      });
      return `${baseUrl}?${params.toString()}`;
    },
    copyQueryToClipboard() {
      const queryUrl = this.assembleQueryUrl();
      navigator.clipboard.writeText(queryUrl).then(() => {
        this.$notify({
          title: "Copied",
          text: "Search URL copied to clipboard!",
          type: "success",
        });
      });
    },
  },
  async created() {
    // here we should parse the query string and set the filters accordingly
    await this.processQueryParams();
  },
  watch: {
    async datasetName(newVal) {
      this.datasetNameLocal = newVal;
      await this.initSearch();
    },
  },
};
</script>

<style scoped></style>
