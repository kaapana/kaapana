<template>
  <v-dialog v-model="show" max-width="70vw">
    <v-card>
      <v-card-title class="headline">
        Datasets
        <v-spacer></v-spacer>
        <v-text-field
          v-model="search"
          append-icon="mdi-magnify"
          label="Search"
          single-line
          hide-details
        ></v-text-field>
      </v-card-title>
      <v-card-text>
        <v-data-table
          :headers="headers"
          :items="datasets"
          sort-by="name"
          :search="search"
        >
          <template v-slot:item.name="{ item }">
            {{ item.name }}
          </template>
          <template v-slot:item.size="{ item }">
            {{ item.size }}
          </template>
          <template v-slot:item.username="{ item }">
            {{ item.username }}
          </template>
          <template v-slot:item.time_created="{ item }">
            {{ new Date(item.time_created).toLocaleString() }}
          </template>
          <template v-slot:item.time_updated="{ item }">
            {{ new Date(item.time_updated).toLocaleString() }}
          </template>
          <template v-slot:item.actions="{ item }">
            <v-icon @click="deleteItem(item)"> mdi-delete </v-icon>
          </template>
        </v-data-table>
      </v-card-text>
      <v-card-actions class="justify-center">
        <v-btn color="primary" @click="show = false">Close</v-btn>
      </v-card-actions>
      <ConfirmationDialog
        :show="dialogDelete"
        title="Delete dataset"
        @cancel="closeDelete"
        @confirm="deleteItemConfirm"
      >
        Are you sure you want to delete the dataset?
      </ConfirmationDialog>
    </v-card>
  </v-dialog>
</template>

<script>
import { loadDatasets, deleteDataset } from "../common/api.service";
import ConfirmationDialog from "@/components/ConfirmationDialog.vue";

export default {
  props: {
    value: {
      type: Boolean,
      required: true,
    },
  },
  components: {
    ConfirmationDialog,
  },
  data() {
    return {
      datasets: [],
      search: null,
      dialogDelete: false,
      headers: [
        {
          text: "Name",
          align: "start",
          value: "name",
        },
        { text: "Size", value: "size" },
        { text: "User", value: "username" },
        { text: "Created", value: "time_created" },
        { text: "Updated", value: "time_updated" },
        { text: "Actions", value: "actions", sortable: false },
      ],
      editedDatasets: false,
    };
  },
  async mounted() {
    this.loadDatasets().then((datasets) => (this.datasets = datasets));
  },
  methods: {
    async loadDatasets() {
      return (await loadDatasets(false)).map((dataset) => ({
        ...dataset,
        size: dataset.identifiers.length,
      }));
    },
    deleteItem(item) {
      this.editedIndex = this.datasets.indexOf(item);
      this.editedItem = Object.assign({}, item);
      this.dialogDelete = true;
    },

    async deleteItemConfirm() {
      const successful = await deleteDataset(this.editedItem.name);
      if (successful) {
        this.$notify({
          title: `Deleted dataset ${this.editedItem.name}`,
          type: "success",
        });
        this.datasets.splice(this.editedIndex, 1);
        this.closeDelete();
        this.editedDatasets = true;
      }
    },

    closeDelete() {
      this.dialogDelete = false;
      this.$nextTick(() => {
        this.editedItem = Object.assign({}, this.defaultItem);
        this.editedIndex = -1;
      });
    },

    close() {
      this.dialog = false;
      this.$nextTick(() => {
        this.editedItem = Object.assign({}, this.defaultItem);
        this.editedIndex = -1;
      });
    },
  },
  computed: {
    show: {
      get() {
        return this.value;
      },
      set(value) {
        this.$emit("close", this.editedDatasets);
      },
    },
  },
  watch: {
    value() {
      this.loadDatasets().then((datasets) => (this.datasets = datasets));
    },
  },
};
</script>
