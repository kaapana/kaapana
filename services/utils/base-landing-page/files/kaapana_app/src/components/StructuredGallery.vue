<template>
  <div>
    <div v-for="studies in patients" :key="JSON.stringify(studies)">
      <v-lazy
        :options="{
          threshold: 0.3,
          delay: 100,
        }"
        transition="fade-transition"
        class="fill-height"
        :min-height="100"
      >
        <PatientView :studies="studies" />
      </v-lazy>
    </div>
  </div>
</template>

<script>
/* eslint-disable */
import PatientView from "./PatientView.vue";

export default {
  props: {
    patients: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {};
  },
  components: {
    PatientView,
  },
  created() {},
  mounted() {},
  methods: {},
  watch: {},
};
</script>
<style></style>
