<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between">
      {{ title }}
    </v-card-title>
    <v-card-text> Username: {{ userInformation.name }} </v-card-text>
    <v-card-text> ID: {{ userInformation.idx }} </v-card-text>
    <v-card-text> First name: {{ userInformation.firstName }} </v-card-text>
    <v-card-text> Last name: {{ userInformation.lastName }} </v-card-text>
    <v-card-text> Email: {{ userInformation.email }} </v-card-text>
    <v-card-text> Attributes: {{ userInformation.attributes }} </v-card-text>
    <v-divider></v-divider>
    <table class="table">
      <thead>
        <th align="left">Groupname</th>
        <th align="left">GroupID</th>
      </thead>
      <tbody>
        <tr v-for="group in userGroups" :key="group.name">
          <td>{{ group.name }}</td>
          <td>{{ group.idx }}</td>
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
        <tr v-for="role in userRoles" :key="role.name">
          <td>{{ role.name }}</td>
          <td>{{ role.idx }}</td>
          <td>{{ role.description }}</td>
        </tr>
      </tbody>
    </table>
    <v-divider></v-divider>
    <v-select
      v-model="new_groups_for_user"
      :items="available_groups"
      item-text="name"
      item-value="idx"
      label="Select groups"
      multiple
    >
    </v-select>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn
        color="primary"
        text
        @click="
          $emit('add-user-to-groups', new_groups_for_user, userInformation);
          new_groups_for_user = [];
        "
      >
        Add user to groups
      </v-btn>
    </v-card-actions>
    <v-select
      v-model="new_roles_for_user"
      :items="available_roles"
      label="Select roles"
      item-text="name"
      multiple
      return-object
    >
    </v-select>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn
        color="primary"
        text
        @click="
          $emit('assign-roles-to-user', new_roles_for_user, userInformation);
          new_roles_for_user = [];
        "
      >
        Assign roles to user
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "UserInformation",

  props: [
    "userInformation",
    "userGroups",
    "userRoles",
    "title",
    "available_groups",
    "available_roles",
  ],

  data() {
    return {
      new_groups_for_user: [],
      new_roles_for_user: [],
    };
  },
};
</script>
