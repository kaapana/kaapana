<template>
  <v-container>
    <h4 class="text-h4 py-8">User Projects</h4>
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
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import axios, { AxiosResponse } from 'axios';

const host = window.location.hostname;
const client = axios.create({
  baseURL: `https://${host}/aii`,
});


type ProjectItem = {
  id: number,
  external_id?: number,
  name: string,
  description?: string,
}

export default defineComponent({
  props: {},
  data() {
    return {
      projects: [] as ProjectItem[],
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
