<template>
  <v-card>
    <v-card-title>
      <v-col cols="4">
        <p class="mx-4 my-2">{{ title }}</p>
      </v-col>
      <v-btn @click="$emit('refresh')">
        <v-icon color="primary" dark large> mdi-refresh </v-icon>
      </v-btn>
      <v-col cols="4">
        <v-btn @click="$emit('add-button')">
          <v-icon color="primary" dark large> mdi-plus </v-icon>
        </v-btn>
      </v-col>
    </v-card-title>

    <v-data-table :headers="columns" :items="rows" item-text="name">
      <template v-slot:item.details="{ item }">
        <v-btn @click="$emit('open-settings', item[identifier])">
          <v-icon color="primary" dark small> mdi-account-cog </v-icon>
        </v-btn>
      </template>
    </v-data-table>
  </v-card>
</template>

<script>
export default {
  name: "UserTable",
  props: {
    columns: Array,
    rows: Array,
    title: String,
    identifier: String,
  },
};
</script>

<style>
.table {
  width: 90%;
  table-layout: auto;
}
</style>
