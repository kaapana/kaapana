<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between">
      {{ title }}
    </v-card-title>
    <v-card-text> Groupname: {{ groupInformation.name }} </v-card-text>
    <v-card-text> GroupID: {{ groupInformation.idx }} </v-card-text>
    <v-divider></v-divider>
    <table class="table">
      <thead>
        <th align="left">Username</th>
        <th align="left">UserID</th>
      </thead>
      <tbody>
        <tr v-for="user in groupUsers" :key="user.name">
          <td>{{ user.name }}</td>
          <td>{{ user.idx }}</td>
        </tr>
      </tbody>
    </table>
    <v-divider></v-divider>
    <table class="table">
      <thead>
        <th align="left">Rolename</th>
        <th align="left">RoleID</th>
        <th align="left">Description</th>
      </thead>
      <tbody>
        <tr v-for="role in groupRoles" :key="role.name">
          <td>{{ role.name }}</td>
          <td>{{ role.idx }}</td>
          <td>{{ role.description }}</td>
        </tr>
      </tbody>
    </table>
  </v-card>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "GroupInformation",
  props: ["groupInformation", "groupUsers", "groupRoles", "title"],
};
</script>
