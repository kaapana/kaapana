<template>
  <v-container>
    <v-row>
      <v-col>
        <v-btn @click="refresh" prepend-icon="mdi-refresh">Check for new Documents</v-btn>
      </v-col>
      <v-col>
        <v-text-field
          autofocus
          label="Search"
          append-inner-icon="mdi-magnify"
          single-line
          v-model="filter"
        ></v-text-field>
      </v-col>
      <v-col>
        <v-select :items="sort_keys" label="Sort by" v-model="sorting_key"></v-select>
      </v-col>
    </v-row>
    <v-row v-if="!loaded">
      <v-col align="center">
        <v-progress-circular indeterminate color="primary"></v-progress-circular>
      </v-col>
    </v-row>
    <v-row v-if="loaded">
      <v-col>
        <v-card class="mx-auto">
          <v-list>
            <v-list-item
              v-for="doc in filtered_documents"
              :key="doc.file_id"
              :title="`${doc.file.path}`"
              :subtitle="`Click to ${doc.action_name} in ${doc.app_name}`"
              :href="doc.url"
              target="_blank"
            >
              <template v-slot:prepend>
                <v-img width="40" :src="doc.favicon" v-if="doc.favicon"></v-img>
                <v-icon icon="mdi-file" v-if="!doc.favicon"></v-icon>
              </template>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { computed } from "vue";

const loaded = ref(false);
const documents = ref<any[]>([]);
const sort_keys = ref([
  { value: "path", title: "Path" },
  { value: "modification_time", title: "Modification Time" },
  { value: "creation_time", title: "Creation Time" },
]);
const sorting_key = ref("modification_time");
const filter = ref("");

const sorted_documents = computed(() =>
  documents.value.sort((a, b) =>
    a.file[sorting_key.value] > b.file[sorting_key.value] ? -1 : 1
  )
);
const filtered_documents = computed(() =>
  sorted_documents.value.filter((doc) =>
    doc.file.path.toLowerCase().includes(filter.value.toLowerCase())
  )
);

function refresh() {
  console.log("Refreshing list");
  loaded.value = false;
  fetch(`./documents/refresh`, { method: "POST" }).then(() => {
    load_documents();
  });
}

function load_documents() {
  console.log("Refreshing list");
  fetch(`./documents/`)
    .then((r) => r.json())
    .then((data) => {
      documents.value = data;
      loaded.value = true;
    });
}

const conn = new WebSocket(
  (window.location.protocol === "https:" ? "wss://" : "ws://") +
    window.location.href.split("//")[1] +
    "ws"
);
conn.onopen = function (event) {
  console.log("Websocket connection established");
};
conn.onmessage = function (event) {
  const msg = JSON.parse(event.data);
  if (msg.type == "update") {
    console.group("Retreived Update");
    load_documents();
  }
};

refresh();
</script>
