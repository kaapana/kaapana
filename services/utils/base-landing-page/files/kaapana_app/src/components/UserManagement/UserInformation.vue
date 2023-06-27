<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between">
      {{ title }}
    </v-card-title>
    <v-card-text> UserInformation: {{ userInformation }} </v-card-text>
    <v-divider></v-divider>
    <v-card-text> Groups: {{ userGroups }} </v-card-text>
    <v-divider></v-divider>
    <v-card-text> Roles: {{ userRoles }} </v-card-text>
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
