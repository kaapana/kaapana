<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between">
      {{ projectName }}
    </v-card-title>
    <v-row>
      <v-col cols="3"><v-card-text> Keycloak group id</v-card-text> </v-col>
      <v-col cols="9"
        ><v-card-text> {{ projectInformation.group_id }}</v-card-text>
      </v-col>
    </v-row>

    <v-container>
      <v-row>
        <v-col cols="3"> <v-card-text> Members </v-card-text></v-col>
        <v-col cols="7">
          <v-autocomplete
            v-model="addMembers"
            :items="computedAvailableUser"
            chips
            multiple
            item-text="name"
            return-object
          >
          </v-autocomplete>
        </v-col>
        <v-col cols="2">
          <v-btn color="primary" text @click="add_member()">
            <v-icon color="primary" dark> mdi-plus </v-icon>
          </v-btn>
        </v-col>
      </v-row>

      <v-data-table :headers="userTableHeaders" :items="projectMembers" item-key="name">
        <template v-slot:item.role="{ item }">
          <v-select
            v-model="item.projectRole.project_role_name"
            :items="projectInformation.project_roles"
            item-text="project_role_name"
            @change="change_user_project_role(item)"
          >
          </v-select>
        </template>
        <template v-slot:item.remove="{ item }">
          <v-btn color="primary" text @click="remove_member(item)">
            <v-icon color="primary" dark> mdi-minus </v-icon>
          </v-btn>
        </template>
      </v-data-table>
    </v-container>
  </v-card>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "ProjectInformation",
  props: ["projectName", "title", "userList"],
  data() {
    return {
      num_members: 0,
      projectMembers: [],
      addMembers: [],
      projectInformation: {
        name: "",
        role_admin_id: "",
        role_member_id: "",
        group_id: "",
        project_roles: [],
      },
      projectRoles: [
        { name: "admin", field: "role_admin_id", id: "" },
        { name: "member", field: "role_member_id", id: "" },
      ],
      userTableHeaders: [
        { text: "Username", value: "name" },
        { text: "Id", value: "id" },
        { text: "Role", value: "role" },
        { text: "Remove", value: "remove" },
      ],
      availableUsers: [],
    };
  },

  watch: {
    projectName() {
      console.log("Watcher projectName: " + this.projectName);
      this.get_project_info();
      this.get_project_users();
    },
  },

  mounted() {
    this.get_project_info();
    this.get_project_users();
  },

  computed: {
    computedAvailableUser() {
      return this.get_available_users();
    },
  },

  methods: {
    remove_member(member) {
      kaapanaApiService
        .kaapanaApiDelete("users/projects/" + this.projectName + "/users/" + member.id)
        .then((response) => {
          console.log("User successfully removed from project.");
        })
        .catch((error) => {
          console.error("Error removing user from project", error);
        });
      this.get_project_users();
    },
    add_member() {
      let payload = this.addMembers.map((user) => user.id);
      let id = this.projectInformation.group_id;
      kaapanaApiService
        .kaapanaApiPut("users/groups/" + id + "/users", (payload = payload))
        .then((response) => {
          console.log("Successfully added user to project");
        })
        .catch((error) => {
          console.error("Error adding users to project", error);
        });
      this.get_project_users();
      this.addMembers = [];
    },
    get_project_info() {
      self = this;
      let payload = { name: self.projectName };
      kaapanaApiService
        .kaapanaApiGet("users/projects/", (payload = payload))
        .then((response) => {
          this.projectInformation = response.data[0];
        })
        .catch((error) => {
          console.error("Error fetching project information:", error);
        });
    },
    get_project_users() {
      let self = this;
      console.log("groupId " + self.projectInformation.group_id);
      kaapanaApiService
        .kaapanaApiGet("users/projects/" + self.projectName + "/users")
        .then((response) => {
          this.projectMembers = response.data;
        })
        .catch((error) => {
          console.error("Error fetching users belonging to group:", error);
        });
    },
    get_available_users() {
      return this.userList.filter((user) => {
        return !this.projectMembers.some((member) => member.id === user.id);
      });
    },
    change_user_project_role(user) {
      let self = this;
      console.log("user id: " + user.id);
      console.log("email: " + user.email);
      console.log("username: " + user.name);
      console.log("project_role_name: " + user.projectRole.project_role_name);
      kaapanaApiService
        .kaapanaApiPut(
          "users/projects/" +
            self.projectName +
            "/user/" +
            user.id +
            "/role/" +
            user.projectRole.project_role_name
        )
        .then((response) => {
          console.log("User role successfully changed!");
        })
        .catch((error) => {
          console.error("Error fetching users belonging to group:", error);
        });
    },
  },
};
</script>
