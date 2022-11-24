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
        />
      </v-col>
      <v-col cols="1" align="center">
        <v-btn @click="addFilter" icon>
          <v-icon>
            mdi-filter-plus-outline
          </v-icon>
        </v-btn>
      </v-col>
      <v-col cols="1" align="center">
        <v-btn v-if="!display_filters && filters.length > 0"
               @click="display_filters = !display_filters" icon>
          <v-icon>
            mdi-filter-menu
          </v-icon>
          ({{ filters.length }})
        </v-btn>
      </v-col>

      <v-col cols="2" align="center">
        <v-btn color="primary" @click="search" style="width: 100%;">Search</v-btn>
      </v-col>
    </v-row>
    <SearchItem
        v-show="display_filters"
        v-for="filter in filters" :key="filter.id"
        :id="filter.id"
        :_item_select="filter._item_select"
        :_key_select="filter._key_select"
        :props_change="display_filters"
        ref="filters"
        @deleteFilter="_id => deleteFilter(_id)"
    />
  </div>
</template>

<script>
/* eslint-disable */
import SearchItem from "./SearchItem.vue";

export default {
  name: "Search",
  props: {
    cohort: {}
  },
  data() {
    return {
      query_string: "",
      display_filters: true,
      filters: [],
      counter: 0,
      item_values: {},
    }
  },
  components: {
    SearchItem
  },
  methods: {
    addFilter() {
      this.display_filters = true
      this.filters.push({
        id: this.counter
      })
      this.counter++
    },
    deleteFilter(id) {
      this.filters = this.filters.filter(filter => filter.id !== id)
    },
    composeQuery() {
      const query = {
        "bool": {
          "must": [
            ...(
                this.$refs.filters !== undefined
                    ? this.$refs.filters.map(filter => filter.query).filter(query => query !== null)
                    : []
            ),
            this.cohort !== null && this.cohort.identifiers && this.cohort.identifiers.length > 0
                ? {
                  "bool": {
                    "should": this.cohort.identifiers.map(item => ({
                          "match": {
                            "0020000E SeriesInstanceUID_keyword.keyword": item['identifier']
                          }
                        })
                    )
                  }
                }
                : '',
            {
              "query_string": {
                "query": "*" + this.query_string + "*"
              }
            }
          ]
        }
      }
      return JSON.stringify(query)
    },
    search() {
      this.display_filters = false
      this.$emit("search", this.composeQuery())
      localStorage['search.filters'] = JSON.stringify(
          (this.$refs.filters !== undefined ?
              this.$refs.filters.map(filter => ({
                'id': filter.id,
                '_key_select': filter.key_select,
                '_item_select': filter.item_select
              })) :
              [])
      )
    },
  },
  mounted() {
    if (localStorage['search.filters']) {
      this.filters = JSON.parse(localStorage['search.filters'])
    }
    if (localStorage['search.query_string']) {
      this.query_string = localStorage['search.query_string']
    }
  },
  watch: {
    query_string() {
      localStorage['search.query_string'] = this.query_string
    },
    cohort() {
      this.search()
    }
  }

}
</script>

<style scoped>

</style>
