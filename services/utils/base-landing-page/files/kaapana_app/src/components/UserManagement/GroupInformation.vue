<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between">
    {{  title }}
    </v-card-title>
    <v-card-text>
      GroupInformation: {{ groupInformation }}
    </v-card-text>
    <v-divider></v-divider>
    <v-card-text>
      Users: {{ groupUsers }}
    </v-card-text>
    <v-divider></v-divider>
    <v-card-text>
      Roles: {{ groupRoles }}
    </v-card-text>
  </v-card>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "GroupInformation",
  props: ['groupInformation','groupUsers','groupRoles','title'],


}

</script>