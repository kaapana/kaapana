<template>
  <v-card>
    <input type="file" @change="fileOnChange" multiple />
  </v-card>
  <!-- <v-card
    @drop.preevent="fileOnChange"
    >
    <v-card-text>
      <v-row class="d-flex flex-column" dense align="center" justify="center">
        <v-icon icon="mdi-cloud-upload"></v-icon>
        <p>Drop your file(s) here to upload them into the CAS.</p>
      </v-row>
    </v-card-text>
  </v-card> -->
  <v-card>
    <v-table>
      <thead>
        <tr>
          <th>Status</th>
          <th>Filename</th>
          <th>URN</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="file in files" :key="file.filename">
          <td>
            <v-icon icon="mdi-check" v-if="file.status == 2"></v-icon>
            <v-progress-circular
              indeterminate
              color="primary"
              v-if="file.status == 1"
            ></v-progress-circular>
            <v-icon icon="mdi-alert-circle" v-if="file.status == 3"></v-icon>
          </td>
          <td>{{ file.filename }}</td>
          <td>
            <div v-if="file.urn">
              <router-link :to="`/urn/${file.urn}`">{{ file.urn }}</router-link>
            </div>
            <div v-if="!file.urn">file is uploading waiting for urn</div>
          </td>
          <td>
            <v-btn
              v-if="file.status == 2"
              icon="mdi-delete"
              @click="(event: Event) => {if (file.urn) {deleteFile(file)}}"
            >
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>
  </v-card>
</template>

<script lang="ts">
import { mapState, mapActions } from "pinia";
import { useCASStore } from "@/store/app";

export default {
  data: () => ({
    dragover: false,
  }),
  computed: {
    ...mapState(useCASStore, ["files"]),
  },
  methods: {
    ...mapActions(useCASStore, ["uploadFile", "deleteFile"]),
    fileOnChange(e: any) {
      var upload_files = e.target.files || e.dataTransfer.files;
      for (const file of upload_files) {
        this.uploadFile(file);
      }
    },
  },
};
</script>
