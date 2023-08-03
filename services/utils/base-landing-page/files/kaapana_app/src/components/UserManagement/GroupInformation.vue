<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between">
      {{ title }}
    </v-card-title>
    <v-card-text> Groupname: {{ groupInformation.name }} </v-card-text>
    <v-card-text> GroupID: {{ groupInformation.id }} </v-card-text>
    <v-divider></v-divider>
    <table class="table">
      <thead>
        <th align="left">Username</th>
        <th align="left">UserID</th>
      </thead>
      <tbody>
        <tr v-for="user in groupUsers" :key="user.name">
          <td>{{ user.name }}</td>
          <td>{{ user.id }}</td>
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
          <td>{{ role.id }}</td>
          <td>{{ role.description }}</td>
        </tr>
      </tbody>
    </table>
    <v-select
      v-model="new_roles_for_group"
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
          assign_roles_to_group(new_roles_for_group, groupInformation);
          new_roles_for_group = [];
        "
      >
        Assign roles to group
      </v-btn>
    </v-card-actions>
    <v-select
      v-model="new_users_for_group"
      :items="available_users"
      label="Select users"
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
          add_users_to_group(new_users_for_group, groupInformation);
          new_users_for_group = [];
        "
      >
        Add users to group
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "GroupInformation",
  props: ["groupId", "title", "roleList", "userList"],
  data() {
    return {
      new_users_for_group: [],
      new_roles_for_group: [],
      groupUsers: [],
      groupRoles: [],
      available_roles: [],
      available_users: [],
      groupInformation: {
        id: "",
        name: "",
      },
    };
  },

  watch: {
    groupId() {
      this.get_group_users();
      this.get_group_roles();
      this.get_group_info();
    },
    groupRoles() {
      this.get_available_roles();
    },
    groupUsers() {
      this.get_available_users();
    },
  },

  mounted() {
    this.get_group_info(),
      this.get_group_users(),
      this.get_group_roles(),
      this.get_available_roles(),
      this.get_available_users();
  },

  computed: {
    computedGroupUsers() {
      return [...this.groupUsers];
    },
    computedGroupRoles() {
      return [...this.groupRoles];
    },
    computedAvailableRoles() {
      return [...this.available_roles];
    },
    computedAvailableUsers() {
      return [...this.available_users];
    },
    computedGroupInfo() {
      return [...this.groupInformation];
    },
  },

  methods: {
    get_group_info() {
      self = this;
      kaapanaApiService
        .kaapanaApiGet("users/groups/" + self.groupId)
        .then((response) => {
          this.groupInformation = response.data;
        })
        .catch((error) => {
          console.error("Error fetching group information:", error);
        });
    },
    get_group_users() {
      let self = this;
      kaapanaApiService
        .kaapanaApiGet("users/groups/" + self.groupId + "/users")
        .then((response) => {
          this.groupUsers = response.data;
        })
        .catch((error) => {
          console.error("Error fetching users belonging to group:", error);
        });
    },
    get_available_users() {
      this.available_users = this.userList.filter((user) => {
        return !this.groupUsers.some((groupUser) => groupUser.id === user.id);
      });
    },
    get_group_roles() {
      let self = this;
      kaapanaApiService
        .kaapanaApiGet("users/groups/" + self.groupId + "/roles")
        .then((response) => {
          this.groupRoles = response.data;
        })
        .catch((error) => {
          console.error("Error fetching roles belonging to group:", error);
        });
    },
    get_available_roles() {
      this.available_roles = this.roleList.filter((role) => {
        return !this.groupRoles.some((groupRole) => groupRole.id === role.id);
      });
    },
    assign_roles_to_group(new_roles_for_group, groupInformation) {
      console.log(new_roles_for_group);
      console.log(groupInformation);
      let id = groupInformation.id;
      let payload = new_roles_for_group;
      kaapanaApiService
        .kaapanaApiPut("users/groups/" + id + "/roles", (payload = payload))
        .then((response) => {
          this.get_group_roles();
        })
        .catch((error) => {
          console.log("Error assigning roles to group", error);
        });
    },
    add_users_to_group(new_users_for_group, groupInformation) {
      let payload = new_users_for_group.map((user) => user.id);
      let id = groupInformation.id;
      kaapanaApiService
        .kaapanaApiPut("users/groups/" + id + "/users", (payload = payload))
        .then((response) => {
          this.get_group_users();
        })
        .catch((error) => {
          console.log("Error adding users to group", error);
        });
    },
  },
};
</script>
