<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between">
      {{ title }}
    </v-card-title>
    <v-card-text> Username: {{ userInformation.name }} </v-card-text>
    <v-card-text> ID: {{ userInformation.id }} </v-card-text>
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
          <td>{{ group.id }}</td>
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
          <td>{{ role.id }}</td>
          <td>{{ role.description }}</td>
        </tr>
      </tbody>
    </table>
    <v-divider></v-divider>
    <v-select
      v-model="new_groups_for_user"
      :items="available_groups"
      item-text="name"
      item-value="id"
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
          add_user_to_groups(new_groups_for_user, userInformation);
          new_groups_for_user = [];
          get_user_groups;
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
          assign_roles_to_user(new_roles_for_user, userInformation);
          new_roles_for_user = [];
          get_user_roles;
          get_available_roles;
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

  props: ["title", "userId", "roleList", "groupList"],

  data() {
    return {
      new_groups_for_user: [],
      new_roles_for_user: [],
      available_groups: [],
      available_roles: [],
      userGroups: [],
      userRoles: [],
      userInformation: {
        username: "",
        email: "",
        firstName: "",
        lastName: "",
        attributes: {},
      },
    };
  },

  watch: {
    userId() {
      this.get_user_groups();
      this.get_user_roles();
      this.get_user_information();
    },
    userRoles() {
      this.get_available_roles();
    },
    userGroups() {
      this.get_available_groups();
    },
  },

  mounted() {
    this.get_user_information(),
      this.get_available_groups(),
      this.get_user_groups(),
      this.get_available_roles(),
      this.get_user_roles();
  },

  computed: {
    computedAvailableGroups() {
      return [...this.available_groups];
    },
    computedUserGroups() {
      return [...this.userGroups];
    },
    computedAvailableRoles() {
      return [...this.available_roles];
    },
    computedUserRoles() {
      return [...this.userRoles];
    },
  },

  methods: {
    get_user_information() {
      self = this;
      kaapanaApiService
        .kaapanaApiGet("users/" + self.userId)
        .then((response) => {
          this.userInformation = response.data;
        })
        .catch((error) => {
          console.error("Error fetching user information:", error);
        });
    },
    add_user_to_groups(new_groups_for_user, userInformation) {
      let id = userInformation.id;
      let payload = new_groups_for_user;
      kaapanaApiService
        .kaapanaApiPut("users/" + id + "/groups", (payload = payload))
        .then((response) => {
          this.get_user_groups();
        })
        .catch((error) => {
          console.log("Error adding user to groups", error);
        });
    },
    get_available_groups() {
      this.available_groups = this.groupList.filter((group) => {
        return !this.userGroups.some((userGroup) => userGroup.id === group.id);
      });
    },
    get_user_groups() {
      let self = this;
      kaapanaApiService
        .kaapanaApiGet("users/" + self.userId + "/groups")
        .then((response) => {
          this.userGroups = response.data;
        })
        .catch((error) => {
          console.error("Error fetching group information about user:", error);
        });
    },
    assign_roles_to_user(new_roles_for_user, userInformation) {
      let id = userInformation.id;
      let payload = new_roles_for_user;
      kaapanaApiService
        .kaapanaApiPut("users/" + id + "/roles", (payload = payload))
        .then((response) => {
          this.get_user_roles();
        })
        .catch((error) => {
          console.log("Error assigning roles to user", error);
        });
    },
    get_available_roles() {
      this.available_roles = this.roleList.filter((role) => {
        return !this.userRoles.some((userRole) => userRole.id === role.id);
      });
    },
    get_user_roles() {
      let self = this;
      kaapanaApiService
        .kaapanaApiGet("users/" + self.userId + "/roles")
        .then((response) => {
          this.userRoles = response.data;
        })
        .catch((error) => {
          console.error("Error fetching roles of user:", error);
        });
    },
  },
};
</script>
