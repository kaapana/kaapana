<template>
  <table class="table">
    <thead>
      <th v-for="col in columns" align="left" :key="col.name">{{ col.title }}</th>
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
</template>
  
<script>
export default {
  name: "UserTable",
  props: {
    columns: Array,
    rows: Array
  },
  
};

</script>
  
<style>
.table {
  width: 90%;
  table-layout: auto;
}
</style>