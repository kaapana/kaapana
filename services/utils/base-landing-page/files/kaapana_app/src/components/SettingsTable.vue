<template>
  <v-data-table
      :headers="headers"
      :items="items"
      sort-by="name"
      :hide-default-footer="true"
  >
    <template v-slot:top>
      <v-toolbar
          flat
      >
        <v-toolbar-title>Dataset UI Settings</v-toolbar-title>
        <v-divider
            inset
            vertical
        ></v-divider>
        <v-spacer></v-spacer>
        <v-dialog
            v-model="dialog"
            max-width="500px"
        >
          <template v-slot:activator="{ on, attrs }">
            <v-btn
                color="primary"
                dark
                class="mb-2"
                v-bind="attrs"
                v-on="on"
            >
              Add Item
            </v-btn>
          </template>
          <v-card>
            <v-card-title>
              <span class="text-h5">{{ formTitle }}</span>
            </v-card-title>

            <v-card-text>
              <v-container>
                <v-row>
                  <v-col>
                    <v-autocomplete
                        v-model="editedItem.name"
                        :items="availableTags"
                        label="Name"
                    ></v-autocomplete>
                  </v-col>
                </v-row>
              </v-container>
            </v-card-text>

            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn
                  text
                  @click="close"
              >
                Cancel
              </v-btn>
              <v-btn
                  color="primary"
                  text
                  @click="save"
              >
                Add
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>
      </v-toolbar>
    </template>
    <template v-slot:item.display="{ item }">
      <v-simple-checkbox
          v-model="item.display"
      ></v-simple-checkbox>
    </template>
    <template v-slot:item.truncate="{ item }">
      <v-simple-checkbox
          v-model="item.truncate"
      ></v-simple-checkbox>
    </template>
    <template v-slot:item.dashboard="{ item }">
      <v-simple-checkbox
          v-model="item.dashboard"
      ></v-simple-checkbox>
    </template>
    <template v-slot:item.actions="{ item }">
      <v-icon
          @click="deleteItemConfirm(item)"
      >
        mdi-delete
      </v-icon>
    </template>
    <template v-slot:no-data>
      <v-btn
          color="primary"
          @click="initialize"
      >
        Reset
      </v-btn>
    </template>
  </v-data-table>
</template>

<script>
import {loadDicomTagMapping} from "@/common/api.service";

export default {
  props: {
    items: {
      type: Array,
      default: () => []
    }
  },
  data: () => ({
    dialog: false,
    headers: [
      {
        text: 'Name',
        align: 'start',
        sortable: false,
        value: 'name',
      },
      {text: 'Display in Datasets', value: 'display'},
      {text: 'Truncate text', value: 'truncate'},
      {text: 'Show in dashboard', value: 'dashboard'},
      {text: 'Actions', value: 'actions', sortable: false},
    ],
    dicomTags: [],
    editedIndex: -1,
    editedItem: {
      name: '',
      display: false,
      truncate: false,
      dashboard: false
    },
    defaultItem: {
      name: '',
      display: false,
      truncate: false,
      dashboard: false
    },
  }),

  computed: {
    formTitle() {
      return this.editedIndex === -1 ? 'Add Item' : 'Edit Item'
    },
    availableTags() {
      return this.dicomTags.filter(item => !this.items.map(i => i.name).includes(item))
    }
  },
  watch: {
    dialog(val) {
      val || this.close()
    },
  },

  created() {
    loadDicomTagMapping().then(data => this.dicomTags = Object.keys(data))
  },
  methods: {
    editItem(item) {
      this.editedIndex = this.items.indexOf(item)
      this.editedItem = Object.assign({}, item)
      this.dialog = true
    },

    deleteItemConfirm(item) {
      this.items.splice(this.items.indexOf(item), 1)
    },

    close() {
      this.dialog = false
      this.$nextTick(() => {
        this.editedItem = Object.assign({}, this.defaultItem)
        this.editedIndex = -1
      })
    },

    save() {
      if (this.editedIndex > -1) {
        Object.assign(this.items[this.editedIndex], this.editedItem)
      } else {
        this.items.push(this.editedItem)
      }
      this.close()
    },
  },
}
</script>

<style scoped>

</style>