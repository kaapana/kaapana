<template>
  <v-card>
    <!-- TITLE -->
    <v-card-title v-if="showConfigTitle">
      Configure {{ extension.name }}
    </v-card-title>

    <v-card-text>
      <v-form ref="formRef" class="px-3">
        <template v-for="(param, key) in extension.extension_params" :key="key">

          <!-- Group title -->
          <span
            v-if="param.type === 'group_name'"
            class="font-weight-bold"
            style="font-size: 25px;"
          >
            {{ param.default }}
          </span>

          <!-- Documentation block -->
          <div v-if="param.type === 'doc'">
            <br />
            <span class="font-weight-bold" style="font-size: 25px;">
              {{ param.title }}
            </span>

            <div
              v-if="param.html"
              v-html="param.html"
            ></div>
          </div>

          <!-- STRING INPUT -->
          <v-text-field
            v-if="param.type === 'string'"
            :label="param.definition ? `${param.definition} (${key})` : key"
            v-model="formValues[key]"
            clearable
            :rules="rulesStr"
          >
            <template v-if="param.help" #append-outer>
              <v-tooltip>
                <template #activator="{ props }">
                  <v-icon v-bind="props">mdi-tooltip-question</v-icon>
                </template>
                <div v-html="param.help"></div>
              </v-tooltip>
            </template>
          </v-text-field>

          <!-- BOOLEAN -->
          <v-checkbox
            v-if="param.type === 'bool' || param.type === 'boolean'"
            :label="param.definition ? `${param.definition} (${key})` : key"
            v-model="formValues[key]"
          >
            <template v-if="param.help" #append>
              <v-tooltip>
                <template #activator="{ props }">
                  <v-icon v-bind="props">mdi-tooltip-question</v-icon>
                </template>
                <div v-html="param.help"></div>
              </v-tooltip>
            </template>
          </v-checkbox>

          <!-- LIST SINGLE -->
          <v-select
            v-if="param.type === 'list_single'"
            :items="param.value"
            :label="param.definition ? `${param.definition} (${key})` : key"
            v-model="formValues[key]"
            clearable
            :rules="rulesSingleList"
          >
            <template v-if="param.help" #append-outer>
              <v-tooltip>
                <template #activator="{ props }">
                  <v-icon v-bind="props">mdi-tooltip-question</v-icon>
                </template>
                <div v-html="param.help"></div>
              </v-tooltip>
            </template>
          </v-select>

          <!-- LIST MULTI -->
          <v-select
            v-if="param.type === 'list_multi'"
            multiple
            :items="param.value"
            :label="param.definition ? `${param.definition} (${key})` : key"
            v-model="formValues[key]"
            clearable
            :rules="rulesMultiList"
          >
            <template v-if="param.help" #append-outer>
              <v-tooltip>
                <template #activator="{ props }">
                  <v-icon v-bind="props">mdi-tooltip-question</v-icon>
                </template>
                <div v-html="param.help"></div>
              </v-tooltip>
            </template>
          </v-select>

        </template>
      </v-form>
    </v-card-text>

    <!-- ACTIONS -->
    <v-card-actions>
      <v-spacer></v-spacer>

      <v-btn color="error" @click="emitClose">
        Abort
      </v-btn>

      <v-btn color="primary" @click="submit">
        {{ extension.multiinstallable === 'yes' ? 'Launch' : 'Install' }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>



<script setup>
import { ref, computed, watch } from "vue";

const props = defineProps({
  extension: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(["close", "submit"]);

/* ---------------------------
   FORM STATE
---------------------------- */
const formRef = ref(null);
const formValues = ref({});

/* ---------------------------
   INITIALIZE PARAM VALUES
---------------------------- */
watch(
  () => props.extension,
  (ext) => {
    formValues.value = {};

    if (!ext || !ext.extension_params) return;

    Object.entries(ext.extension_params).forEach(([key, param]) => {
      switch (param.type) {
        case "bool":
        case "boolean":
          formValues.value[key] = param.default === true || param.default === "true";
          break;
        case "string":
          formValues.value[key] = param.default ?? "";
          break;
        case "list_single":
          formValues.value[key] = param.default ?? null;
          break;
        case "list_multi":
          formValues.value[key] = param.default ?? [];
          break;
        default:
          break;
      }
    });
  },
  { immediate: true }
);

/* ---------------------------
   TITLE CONDITION
---------------------------- */
const showConfigTitle = computed(() => {
  const params = props.extension?.extension_params;
  if (!params || params === "null") return false;
  const firstKey = Object.keys(params)[0];
  if (!firstKey) return false;
  return params[firstKey].type !== "doc";
});

/* ---------------------------
   VALIDATION RULES
---------------------------- */
const rulesStr = [
  (v) => (v !== null && v !== undefined && v !== "") || "Field is required"
];

const rulesSingleList = [
  (v) => (v !== null && v !== "") || "Please select a value"
];

const rulesMultiList = [
  (v) => (Array.isArray(v) && v.length > 0) || "Select at least one item"
];

/* ---------------------------
   ACTIONS
---------------------------- */
function emitClose() {
  emit("close");
}

async function submit() {
  const valid = await formRef.value.validate();
  if (!valid) return;

  emit("submit", {
    extension: props.extension,
    values: formValues.value
  });
}
</script>

<style scoped>
.font-weight-bold {
  font-weight: bold;
}
</style>
