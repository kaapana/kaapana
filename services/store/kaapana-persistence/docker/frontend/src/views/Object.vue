<template>
  <v-container>
    <v-select
      v-model="schema_urn"
      :items="schema_urns"
      label="Schema"
    ></v-select>
  </v-container>
  <v-expansion-panels v-if="schema_urn">
    <v-expansion-panel v-for="object_urn in object_urns">
      <v-expansion-panel-title>{{ object_urn }}</v-expansion-panel-title>
      <v-expansion-panel-text>
        <ObjectJsonView :urn="object_urn"></ObjectJsonView>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script lang="ts">
import { mapState, mapActions } from "pinia";
import { useSchemaStore } from "@/store/app";
import ObjectJsonView from "@/components/ObjectJsonView.vue";
export default {
  data() {
    return {
      schema_urn: "",
    };
  },
  watch: {
    schema_urn: function (new_schema_urn) {
      this.fetchObjectURNs(new_schema_urn);
    },
  },
  computed: {
    ...mapState(useSchemaStore, ["schema_urns", "object_urns"]),
  },
  methods: {
    ...mapActions(useSchemaStore, ["fetchSchemaURNs", "fetchObjectURNs"]),
  },
  mounted() {
    this.fetchSchemaURNs();
  },
  components: {
    ObjectJsonView,
  },
};
</script>
