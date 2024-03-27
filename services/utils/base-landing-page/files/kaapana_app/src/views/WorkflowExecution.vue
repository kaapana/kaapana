<template>
  <v-container w-50 text-left fluid>
    <IdleTracker />
    <v-row justify="center">
      <v-col sm="12" md="6" xl="4">
        <workflow-execution></workflow-execution>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import WorkflowExecution from "@/components/WorkflowExecution.vue";
import IdleTracker from "@/components/IdleTracker.vue";
export default {
  components: {
    WorkflowExecution,
    IdleTracker,
  },
  data: () => ({}),
  created() { },
  mounted() { },
  watch: {},
  computed: {},
  methods: {},
};
</script>

<style lang="scss"></style>
