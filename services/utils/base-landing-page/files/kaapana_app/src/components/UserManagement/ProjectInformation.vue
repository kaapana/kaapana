<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between">
      {{ title }}
    </v-card-title>
    <v-card-text> Projectname: {{ projectName }} </v-card-text>
  </v-card>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "ProjectInformation",
  props: ["projectName", "title"],
  data() {
    return {
      new_users_for_group: [],
      new_roles_for_group: [],
      groupUsers: [],
      groupRoles: [],
      available_roles: [],
      available_users: [],
      groupInformation: {
        idx: "",
        name: "",
      },
    };
  },

  watch: {},

  mounted() {},

  computed: {},

  methods: {},
};
</script>
