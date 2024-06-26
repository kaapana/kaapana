<template>
  <div>
    <v-row dense align="center">
      <v-col cols="1" align="center">
        <v-icon>mdi-magnify</v-icon>
      </v-col>
      <v-col cols="7">
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
  loadDatasetByName,
  loadFieldNames,
  loadValues,
} from "../common/api.service";
import SaveDatasetDialog from "@/components/SaveDatasetDialog.vue";

export default {
  name: "Search",
  props: {
    datasetName: null,
  },
  data() {
    return {
      query_string: "",
      display_filters: true,
      filters: [],
      counter: 0,
      fieldNames: [],
      mapping: {},
      dialog: false,
    };
  },
  components: { SaveDatasetDialog },
  methods: {
    addFilterItem(key, value) {
      const filters = this.filters.filter(
        (filter) => filter.key_select === key
      );
      if (
        filters.length > 0 &&
        filters[0].item_select.filter((item) => item === value).length === 0
      ) {
        filters[0].item_select.push(value);
        this.display_filters = true;
      } else if (filters.length === 0) {
        loadValues(key, this.constructDatasetQuery() || {}).then((res) => {
          this.mapping[key] = res.data;
          this.filters.push({
            id: this.counter++,
            key_select: key,
            item_select: [value],
          });
        });

        this.display_filters = true;
      }
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
      // console.log(JSON.stringify(query));
      return query;
    },
    async search(onMount = false) {
      this.display_filters = onMount;
      this.$emit("search", await this.composeQuery());
      // localStorage['Dataset.search.filters'] = JSON.stringify(
      //     this.filters.map(filter => (
      //         {
      //           'id': filter.id,
      //           'key_select': filter.key_select,
      //           'item_select': filter.item_select
      //         })
      //     )
      // )
      // localStorage['Dataset.search.query_string'] = JSON.stringify(this.query_string)
      // localStorage['Dataset.search.datasetName'] = JSON.stringify(this.datasetName)
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
      loadValues(key, this.constructDatasetQuery() || {}).then((res) => {
        this.mapping[key] = res.data;
      });
    },
    async reloadDataset(){
      this.dataset =
        this.datasetName && (await loadDatasetByName(this.datasetName));
    },
    async initSearch(onMount = false) {
      this.filters = [];
      this.dataset =
        this.datasetName && (await loadDatasetByName(this.datasetName));
      this.search(onMount);
      loadFieldNames().then((res) => {
        this.fieldNames = res.data;
        this.mapping = Object.assign(
          {},
          ...this.fieldNames.map((_name) => ({
            [_name]: { items: [], key: "" },
          }))
        );
      });
    },
  },
  async mounted() {
    await this.initSearch(true);

    // this.filters = JSON.parse(localStorage['Dataset.search.filters'] || "[]")
    // this.counter = this.filters.length
    // this.query_string = JSON.parse(localStorage['Dataset.search.query_string'] || "")
    // await this.search(true)
  },
  watch: {
    async datasetName() {
      await this.initSearch(false);
    },
  },
};
</script>

<style scoped></style>
