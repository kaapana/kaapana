<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between">
      {{ title }}
    </v-card-title>
    <table class="table">
      <thead>
        <th align="left">User</th>
        <th align="left">Permissions</th>
      </thead>
      <tbody>
        <tr v-for="acl in accesslistentrees" :key="acl.id">
          <td>{{ acl.user }}</td>
          <td>{{ acl.permissions }}</td>
        </tr>
      </tbody>
    </table>
  </v-card>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "AccessableInformation",

  props: ["title", "accesslistentrees"],

  watch: {},

  mounted() {},

  computed: {},

  methods: {},
};
</script>
