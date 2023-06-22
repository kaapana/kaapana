<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between">
      {{ title }}
    </v-card-title>
    <v-card-text>
      <v-container>
        <v-row v-for="row in fields" :key="row.name">
          <v-text-field v-model="newObject[row.name]" required="">
            <template v-slot:label>
              <span>
                {{ row.label }}
              </span>
            </template>
          </v-text-field>
        </v-row>
      </v-container>
    </v-card-text>
    <v-divider></v-divider>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn color="primary" text @click="$emit('create-object')"> Submit </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import kaapanaApiService from "@/common/kaapanaApi.service";

export default {
  name: "CreateUser",
  props: ["newObject", "fields", "title"],
};
</script>
