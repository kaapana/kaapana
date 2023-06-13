<template>
  <v-card>
    <v-card-title>
      <v-col cols="4">
        <p class="mx-4 my-2">User List</p>
      </v-col>
      <v-btn @click="get_users">
        <v-icon color="primary" dark large>
          mdi-refresh
        </v-icon> 
      </v-btn>
      <v-col cols="4">
        <v-btn @click="createUserDialog = true">
        <v-icon color="primary" dark large>
          mdi-plus
        </v-icon> 
      </v-btn>
      </v-col>
    </v-card-title>

    <UserTable 
      :rows="computedUserList" 
      :columns="columns"
      @open-settings="open_settings">
      <template v-slot:cell="{type, value}">
        <component :is="type" v-bind="value"/>
      </template>
    </UserTable>

    <v-dialog v-model="userInformationField" width="500">
      <v-card-text>
        UserInformation: {{ userInformation }}
      </v-card-text>
    </v-dialog>

    <v-dialog v-model="createUserDialog" width="500">
      <CreateUser 
        :newUser="newUser" 
        @post-user="post_user">
      </CreateUser>
    </v-dialog>
  </v-card>
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

const TextCell = {
  props: ["content"],
  render(h) {
    return h("span", `${this.content}`);
  }
};

export default {
  name: 'iframe-view',
  components: {
    IFrameWindow,
    TextCell,
    UserTable,
    CreateUser
  },
  data() {
    return {
      userId: "00000000000000",
      userInformation: {
        username: "",
        email: "",
        firstName: "",
        lastName: "",
        attributes: {}
      },
      createUserDialog: false,
      addToGroupDialog: false,
      userInformationField: false,
      newUser: { 
        username: "",
        email: "",
        firstName: "",
        lastName: "",
        attributes: {}
      },
      userList: [],
      groupList: [
        { idx: 'w98fjß8jdß83jdfß9a8fjß38j', name: 'non-existing group'}
      ],
      columns: [
        { name: "name", title:"Username", type: "TextCell"},
        { name: "idx", title: "User-ID", type: "TextCell" },
        { name: "firstName", title:"First Name", type: "TextCell"},
        { name: "lastName", title:"Last Name", type: "TextCell"},
        { name: "email", title:"Email", type: "TextCell"},
        { name: "actions", title:"Actions"},
      ]
    };
  },

  mounted() {
    this.get_users()
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
    open_settings(idx) {
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
    },
    post_user() {
      let params = this.newUser;
      kaapanaApiService
      .kaapanaApiPost("users/user", params=params)
      .then((response) => {
        this.createUserDialog = false;
        this.get_users();
      })
      .catch(error => {
        console.log('Error creating user', error);
        this.createUserDialog = false;
      })
    }
  }
}
</script>

<style lang="scss">

</style>
