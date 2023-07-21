<template>
  <div>
    <v-card>
      <v-card-title class="d-flex justify-space-between"> User Management </v-card-title>
      <UserTable
        title="Users"
        :rows="computedUserList"
        :columns="userColumns"
        identifier="idx"
        @open-settings="open_user_info"
        @refresh="get_users"
        @add-button="createUserDialog = true"
      >
      </UserTable>

      <UserTable
        title="Groups"
        :rows="computedGroupList"
        :columns="groupColumns"
        identifier="idx"
        @open-settings="open_group_info"
        @refresh="get_groups"
        @add-button="createGroupDialog = true"
      >
      </UserTable>

      <UserTable
        title="Projects"
        :rows="computedProjectList"
        :columns="projectColumns"
        identifier="name"
        @open-settings="open_project_info"
        @add-button="createProjectDialog = true"
      >
      </UserTable>

      <v-dialog v-model="userInformationField" width="500">
        <UserInformation
          title="User details"
          :userId="userId"
          :roleList="roleList"
          :groupList="groupList"
        >
        </UserInformation>
      </v-dialog>

      <v-dialog v-model="groupInformationField" width="500">
        <GroupInformation
          title="Group details"
          :groupId="groupId"
          :userList="userList"
          :roleList="roleList"
        >
        </GroupInformation>
      </v-dialog>

      <v-dialog v-model="projectInformationField" width="500">
        <ProjectInformation title="Project details" :projectName="projectName">
        </ProjectInformation>
      </v-dialog>

      <v-dialog v-model="createUserDialog" width="500">
        <CreateUser
          title="Create user"
          :newObject="newUser"
          :fields="createUserFields"
          @create-object="post_user"
        >
        </CreateUser>
      </v-dialog>

      <v-dialog v-model="createGroupDialog" width="500">
        <CreateUser
          title="Create group"
          :newObject="newGroup"
          :fields="createGroupFields"
          @create-object="post_group"
        >
        </CreateUser>
      </v-dialog>

      <v-dialog v-model="createProjectDialog" width="500">
        <CreateUser
          title="Create project"
          :newObject="newProject"
          :fields="createProjectFields"
          @create-object="post_project"
        >
        </CreateUser>
      </v-dialog>
    </v-card>
  </div>
</template>

<script>
// @ is an alias to /src
import Vue from "vue";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

import IFrameWindow from "@/components/IFrameWindow.vue";
import UserTable from "@/components/UserManagement/UserTable.vue";
import CreateUser from "@/components/UserManagement/CreateUser.vue";
import UserInformation from "@/components/UserManagement/UserInformation.vue";
import GroupInformation from "@/components/UserManagement/GroupInformation.vue";
import ProjectInformation from "@/components/UserManagement/ProjectInformation.vue";

export default {
  name: "iframe-view",
  components: {
    IFrameWindow,
    UserTable,
    CreateUser,
    UserInformation,
    GroupInformation,
    ProjectInformation,
  },
  data() {
    return {
      userId: "",
      userGroups: [],
      userRoles: [],
      createUserDialog: false,
      createGroupDialog: false,
      createProjectDialog: false,
      addToGroupDialog: false,
      userInformationField: false,
      groupInformationField: false,
      projectInformationField: false,

      groupId: "",
      groupUsers: [],
      groupRoles: [],

      newGroup: {
        groupname: "",
      },

      projectName: "",
      newProject: {
        name: "",
      },

      newUser: {
        username: "",
        email: "",
        firstName: "",
        lastName: "",
        attributes: {},
      },
      userList: [],
      groupList: [],
      roleList: [],
      projectList: [],
      createUserFields: [
        { name: "username", label: "Username" },
        { name: "firstName", label: "First Name" },
        { name: "lastName", label: "Last Name" },
        { name: "email", label: "Email" },
      ],
      createGroupFields: [{ name: "groupname", label: "Groupname" }],
      createProjectFields: [{ name: "name", label: "Projectname" }],
      userColumns: [
        { name: "name", title: "Username" },
        { name: "idx", title: "User-ID" },
        { name: "firstName", title: "First Name" },
        { name: "lastName", title: "Last Name" },
        { name: "email", title: "Email" },
      ],
      groupColumns: [
        { name: "name", title: "Groupname" },
        { name: "idx", title: "Group-ID" },
      ],
      projectColumns: [{ name: "name", title: "Project name" }],
    };
  },

  mounted() {
    this.get_users(),
      this.get_groups(),
      this.get_available_realm_roles(),
      this.get_projects();
  },

  computed: {
    computedGroupList() {
      return [...this.groupList];
    },
    computedUserList() {
      return [...this.userList];
    },
    computedRoleList() {
      return [...this.roleList];
    },
    computedProjectList() {
      return [...this.projectList];
    },
  },

  methods: {
    get_groups() {
      kaapanaApiService
        .kaapanaApiGet("users/groups")
        .then((response) => {
          this.groupList = response.data;
        })
        .catch((error) => {
          console.error("Error fetching group list:", error);
        });
    },
    get_users() {
      kaapanaApiService
        .kaapanaApiGet("users/")
        .then((response) => {
          this.userList = response.data;
        })
        .catch((error) => {
          console.error("Error fetching user list:", error);
        });
    },
    get_available_realm_roles() {
      kaapanaApiService
        .kaapanaApiGet("users/roles")
        .then((response) => {
          this.roleList = response.data;
        })
        .catch((error) => {
          console.error("Error fetching roles list:", error);
        });
    },
    get_projects() {
      kaapanaApiService
        .kaapanaApiGet("users/projects/")
        .then((response) => {
          this.projectList = response.data;
        })
        .catch((error) => {
          console.error("Error fetching project list:", error);
        });
      console.log(this.projectList);
    },
    open_user_info(idx) {
      (this.userInformationField = true), (this.userId = idx);
    },
    open_group_info(idx) {
      (this.groupInformationField = true), (this.groupId = idx);
    },
    open_project_info(name) {
      console.log(name);
      (this.projectInformationField = true), (this.projectName = name);
    },
    post_user() {
      let params = this.newUser;
      kaapanaApiService
        .kaapanaApiPost("users/", (params = params))
        .then((response) => {
          this.createUserDialog = false;
          this.get_users();
        })
        .catch((error) => {
          console.log("Error creating user", error);
          this.createUserDialog = false;
        });
    },
    post_group() {
      let params = this.newGroup;
      kaapanaApiService
        .kaapanaApiPost("users/groups", (params = params))
        .then((response) => {
          this.createGroupDialog = false;
          this.get_groups();
        })
        .catch((error) => {
          console.log("Error creating user", error);
          this.createGroupDialog = false;
        });
    },
    post_project() {
      let params = this.newProject;
      kaapanaApiService
        .kaapanaApiPost("users/projects/" + this.newProject.name)
        .then((response) => {
          this.createProjectDialog = false;
          this.get_projects();
        })
        .catch((error) => {
          console.log("Error creating project", error);
          this.createProjectDialog = false;
        });
    },
  },
};
</script>

<style lang="scss"></style>
