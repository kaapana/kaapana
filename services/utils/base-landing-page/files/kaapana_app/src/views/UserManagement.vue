<template>
  <div>
    <v-card>
      <v-card-title class="d-flex justify-space-between">
      User Management
      </v-card-title>
      <UserTable
        title="Users"
        :rows="computedUserList" 
        :columns="userColumns" 
        @open-settings="open_user_info"
        @refresh="get_users"
        @add-button="createUserDialog = true">
      </UserTable>

      <UserTable 
        title="Groups"
        :rows="computedGroupList" 
        :columns="groupColumns" 
        @open-settings="open_group_info"
        @refresh="get_groups"
        @add-button="createGroupDialog = true">
      </UserTable>

      <v-dialog v-model="userInformationField" width="500">
        <UserInformation title='User details' :userInformation="userInformation" :userGroups="userGroups"
          :userRoles="userRoles">
        </UserInformation>
      </v-dialog>

      <v-dialog v-model="groupInformationField" width="500">
        <GroupInformation title="Group details" :groupInformation="groupInformation" :groupUsers="groupUsers"
          :groupRoles="groupRoles">
        </GroupInformation>
      </v-dialog>

      <v-dialog v-model="createUserDialog" width="500">
        <CreateUser 
          title="Create user"
          :newObject="newUser"
          :fields="createUserFields"
          @create-object="post_user">
        </CreateUser>
      </v-dialog>

      <v-dialog v-model="createGroupDialog" width="500">
        <CreateUser
          title="Create group"
          :newObject="newGroup"
          :fields="createGroupFields"
          @create-object="post_group">
        </CreateUser>
      </v-dialog>
    </v-card>
  </div>
</template>


<script>
// @ is an alias to /src
import Vue from 'vue'
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

import IFrameWindow from "@/components/IFrameWindow.vue";
import UserTable from "@/components/UserManagement/UserTable.vue";
import CreateUser from "@/components/UserManagement/CreateUser.vue"
import UserInformation from "@/components/UserManagement/UserInformation.vue"
import GroupInformation from "@/components/UserManagement/GroupInformation.vue"


export default {
  name: 'iframe-view',
  components: {
    IFrameWindow,
    UserTable,
    CreateUser,
    UserInformation,
    GroupInformation
  },
  data() {
    return {
      userId: "",
      userInformation: {
        username: "",
        email: "",
        firstName: "",
        lastName: "",
        attributes: {}
      },
      userGroups: [],
      userRoles: [],
      createUserDialog: false,
      createGroupDialog: false,
      addToGroupDialog: false,
      userInformationField: false,
      groupInformationField: false,

      groupId: "",
      groupInformation: {
        idx: "",
        name: ""
      },

      groupUsers: [],
      groupRoles: [],

      newGroup: {
        groupname: "",
      },

      newUser: {
        username: "",
        email: "",
        firstName: "",
        lastName: "",
        attributes: {}
      },
      userList: [],
      groupList: [],
      createUserFields: [
        { name: "username", label: "Username"},
        { name: "firstName", label: "First Name"},
        { name: "lastName", label: "Last Name"},
        { name: "email", label: "Email"},
      ],
      createGroupFields: [
        { name: "groupname", label: "Groupname" },
      ],
      userColumns: [
        { name: "name", title: "Username" },
        { name: "idx", title: "User-ID" },
        { name: "firstName", title: "First Name" },
        { name: "lastName", title: "Last Name" },
        { name: "email", title: "Email" },
      ],
      groupColumns: [
        { name: "name", title: "Groupname" },
        { name: "idx", title: "Group-ID" }
      ]
    };
  },

  mounted() {
    this.get_users(),
      this.get_groups()
  },

  computed: {
    computedGroupList() {
      return [...this.groupList];
    },
    computedUserList() {
      return [...this.userList];
    },
  },

  methods: {
    get_groups() {
      kaapanaApiService
        .kaapanaApiGet("users/groups")
        .then((response) => {
          this.groupList = response.data;
        })
        .catch(error => {
          console.error('Error fetching group list:', error);
        });
    },
    get_users() {
      kaapanaApiService
        .kaapanaApiGet("users/")
        .then((response) => {
          this.userList = response.data;
        })
        .catch(error => {
          console.error('Error fetching user list:', error);
        });
    },
    open_user_info(idx) {
      this.userInformationField = true,
        this.userId = idx
      kaapanaApiService
        .kaapanaApiGet("users/" + this.userId)
        .then((response) => {
          this.userInformation = response.data;
        })
        .catch(error => {
          console.error('Error fetching user information:', error);
        });
      kaapanaApiService
        .kaapanaApiGet("users/" + this.userId + "/groups")
        .then((response) => {
          this.userGroups = response.data;
        })
        .catch(error => {
          console.error('Error fetching group information about user:', error);
        });
      kaapanaApiService
        .kaapanaApiGet("users/" + this.userId + "/roles")
        .then((response) => {
          this.userRoles = response.data;
        })
        .catch(error => {
          console.error('Error fetching roles of user:', error);
        });
    },

    open_group_info(idx) {
      this.groupInformationField = true,
        this.groupId = idx
      kaapanaApiService
        .kaapanaApiGet("users/groups/" + this.groupId)
        .then((response) => {
          this.groupInformation = response.data;
        })
        .catch(error => {
          console.error('Error fetching group information:', error);
        });
      kaapanaApiService
        .kaapanaApiGet("users/groups/" + this.groupId + "/users")
        .then((response) => {
          this.groupUsers = response.data;
        })
        .catch(error => {
          console.error('Error fetching users belonging to group:', error);
        });
      kaapanaApiService
        .kaapanaApiGet("users/groups/" + this.groupId + "/roles")
        .then((response) => {
          this.groupRoles = response.data;
        })
        .catch(error => {
          console.error('Error fetching roles belonging to group:', error);
        });
    },
    post_user() {
      let params = this.newUser;
      kaapanaApiService
        .kaapanaApiPost("users/user", params = params)
        .then((response) => {
          this.createUserDialog = false;
          this.get_users();
        })
        .catch(error => {
          console.log('Error creating user', error);
          this.createUserDialog = false;
        })
    },
    post_group() {
      let params = this.newGroup;
      kaapanaApiService
        .kaapanaApiPost("users/group", params = params)
        .then((response) => {
          this.createGroupDialog = false;
          this.get_groups();
        })
        .catch(error => {
          console.log('Error creating user', error);
          this.createGroupDialog = false;
        })
    }
  }
}
</script>

<style lang="scss"></style>
