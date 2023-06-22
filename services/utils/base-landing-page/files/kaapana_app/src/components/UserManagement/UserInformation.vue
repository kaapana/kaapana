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
      label="Select a group"
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
  </v-card>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "UserInformation",

  props: ["userInformation", "userGroups", "userRoles", "title", "available_groups"],

  data() {
    return {
      new_groups_for_user: [],
    };
  },
};
</script>
