<template>
  <v-container max-width="1200">
    <v-row justify="space-between">
      <v-col cols="6">
        <h4 class="text-h4 py-8">Available Projects</h4>
      </v-col>
      <v-col cols="3" class="d-flex justify-end align-center">
        <v-btn block
          @click="dialog = true" 
          size="large"
          prepend-icon="mdi-plus-box"
        >
          Create New Projects
        </v-btn>
      </v-col>
    </v-row>
    <v-table>
      <thead>
        <tr>
          <th class="text-left">
            Project ID
          </th>
          <th class="text-left">
            Name
          </th>
          <th class="text-left">
            Description
          </th>
          <th class="text-left">
            External ID
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in projects" :key="item.name">
          <td>{{ item.id }}</td>
          <td>{{ item.name }}</td>
          <td>{{ item.description }}</td>
          <td>{{ item.external_id }}</td>
        </tr>
      </tbody>
    </v-table>
  </v-container>
  <v-dialog v-model="dialog" max-width="1000">
    <CreateNewProjectForm :onsubmit="() => dialog = false"/>
  </v-dialog>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import axios, { AxiosResponse } from 'axios';
import CreateNewProjectFrom from '../components/CreateNewProjectForm.vue'

const ACCESS_INFORMATION_BACKEND = import.meta.env.VITE_APP_ACCESS_INFORMATION_BACKEND || '/aii/';
const client = axios.create({
  baseURL: ACCESS_INFORMATION_BACKEND,
});


type ProjectItem = {
  id: number,
  external_id?: number,
  name: string,
  description?: string,
}

export default defineComponent({
  components: {
    CreateNewProjectFrom
  },
  props: {},
  data() {
    return {
      projects: [] as ProjectItem[],
      dialog: false,
    }
  },
  mounted() {
    try {
      client.get('projects').then((resp: AxiosResponse) => {
        this.projects = resp.data as ProjectItem[]
      })
    } catch (error: unknown) {
      console.log(error)
    }
  },
})
</script>
