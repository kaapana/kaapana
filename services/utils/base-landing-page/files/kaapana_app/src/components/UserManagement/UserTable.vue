<template>
  <v-card>
    <v-card-title>
      <v-col cols="4">
        <p class="mx-4 my-2">{{ title }}</p>
      </v-col>
      <v-btn @click="$emit('refresh')">
        <v-icon color="primary" dark large>
          mdi-refresh
        </v-icon>
      </v-btn>
      <v-col cols="4">
        <v-btn @click="$emit('add-button')">
          <v-icon color="primary" dark large>
            mdi-plus
          </v-icon>
        </v-btn>
      </v-col>
    </v-card-title>
    <table class="table">
      <thead>
        <th v-for="col in columns" align="left" :key="col.name">{{ col.title }}</th>
        <th align="left">Details</th>
      </thead>
      <tbody>
        <tr v-for="(row, index) in rows" :key="index">
          <td v-for="col in columns">{{ row[col.name] }}</td>
          <td>
            <v-btn @click="$emit('open-settings', row['idx'])">
              <v-icon color="primary" dark small>
                mdi-account-cog
              </v-icon>
            </v-btn>
          </td>
        </tr>
      </tbody>
    </table>
  </v-card>
</template>
  
<script>
export default {
  name: "UserTable",
  props: {
    columns: Array,
    rows: Array,
    title: String
  },
  
};

</script>
  
<style>
.table {
  width: 90%;
  table-layout: auto;
}
</style>