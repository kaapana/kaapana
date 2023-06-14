<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between">
      Create group
    </v-card-title>
    <v-card-text>
      <v-container>
        <v-row>
          <v-text-field v-model="newGroup.username" label="Username" required=""></v-text-field>
        </v-row>
        <v-row>
          <v-text-field v-model="newGroup.firstName" label="First Name" required=""></v-text-field>
        </v-row>
        <v-row>
          <v-text-field v-model="newGroup.lastName" label="Last Name" required=""></v-text-field>
        </v-row>
        <v-row>
          <v-text-field v-model="newGroup.email" label="Email" required=""></v-text-field>
        </v-row>
        <v-row>
          <v-text-field v-model="newGroup.attributes" label="Attributes" required=""></v-text-field>
        </v-row>
      </v-container>
    </v-card-text>
    <v-divider></v-divider>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn color="primary" text @click="$emit('post-user')">
        Create user
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "CreateGroup",
  props: ['newGroup'],


}

</script>