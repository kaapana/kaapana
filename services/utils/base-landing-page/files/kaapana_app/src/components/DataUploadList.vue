
<template>
  <div>
    <v-data-table :headers="headers" :items="jobs" :items-per-page=5>
      <template v-slot:item.status="{ item }">
        <v-chip
          :color="getStatusColor(item.status)"
          class="ml-1 my-chip"
          dense
          small
          outlined
        >
          {{ item.status }}
        </v-chip>
      </template>
    </v-data-table>
  </div>
</template>
  
<script>

export default {
  name: "DataUploadList",
  data() {
    return {
      filenames: [],
      headers: [
        {
          text: "Filename",
          value: "filename",
        },
        {
          text: "Status",
          value: "status",
        },
      ],
    };
  },
  props: {
    jobs: {
      type: Array,
      default: () => [],
    },
  },
  methods: {
    getStatusColor(status) {
      const statusColors = {
        waiting: "white",
        queued: 'grey',
        scheduled: 'blue',
        pending: 'orange',
        running: 'green',
        finished: 'blue-grey',
        failed: 'red'
      }

      return statusColors[status];
    },
  },
  computed: {},
};
</script>