<template>
  <v-card>
    <!-- TITLE -->
    <v-card-title v-if="showConfigTitle">
      Configure {{ extension.annotations['ui-visible-name'] }}
    </v-card-title>

    <v-card-text>
      <v-form ref="formRef" class="px-3">
        <template v-for="(param, key) in (extension?.extension_params || {})" :key="key">

          <!-- Group title -->
          <span v-if="param.type === 'group_name'" class="text-h6">
            {{ param.default }}
          </span>

          <!-- Documentation block -->
          <div v-if="param.type === 'doc'">
            <br />
            <span class="text-h6">
              {{ param.title }}
            </span>

            <!-- HTML from the extension's own chart, which the platform already trusts to run. -->
            <div v-if="param.html" v-html="param.html"></div>
          </div>

          <!-- STRING INPUT -->
          <v-text-field
            v-if="param.type === 'string'"
            :label="param.definition ? `${param.definition} (${key})` : key"
            v-model="formValues[key]"
            clearable
            :rules="rulesStr"
          >
            <template v-if="param.help" #append>
              <HelpIcon :text="param.help" />
            </template>
          </v-text-field>

          <!-- BOOLEAN -->
          <v-checkbox
            v-if="param.type === 'bool' || param.type === 'boolean'"
            :label="param.definition ? `${param.definition} (${key})` : key"
            v-model="formValues[key]"
          >
            <template v-if="param.help" #append>
              <HelpIcon :text="param.help" />
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
            <template v-if="param.help" #append>
              <HelpIcon :text="param.help" />
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
            <template v-if="param.help" #append>
              <HelpIcon :text="param.help" />
            </template>
          </v-select>

        </template>
      </v-form>
    </v-card-text>

    <!-- ACTIONS -->
    <v-card-actions>
      <v-spacer></v-spacer>

      <v-btn :disabled="busy" @click="emitClose">Cancel</v-btn>

      <v-btn color="primary" :loading="busy" :disabled="busy" @click="submit">
        {{ extension?.multiinstallable === 'yes' ? 'Launch' : 'Install' }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>



<script setup>
import { ref, computed, watch } from 'vue'
import { HelpIcon } from '@kaapana/base-ui'

const props = defineProps({
  busy: { type: Boolean, default: false },
  extension: {
    type: Object,
    required: false,
    default: () => ({
      multiinstallable: 'no',
      name: '',
      version: '',
      keywords: [],
      extension_params: {},
      annotations: { 'ui-visible-name': '' },
      releaseName: ''
    })
  }
});

const emit = defineEmits(['close', 'submit', 'update:dirty'])

/* ---------------------------
   FORM STATE
---------------------------- */
const formRef = ref(null)
const formValues = ref({})
const initialValues = ref({})

/* ---------------------------
   INITIALIZE PARAM VALUES
---------------------------- */
watch(
  () => props.extension,
  (ext) => {
    formValues.value = {}
    initialValues.value = {}

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
    })
    initialValues.value = JSON.parse(JSON.stringify(formValues.value))
  },
  { immediate: true }
);

watch(
  () => JSON.stringify(formValues.value) !== JSON.stringify(initialValues.value),
  (dirty) => emit('update:dirty', dirty),
  { immediate: true },
)

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
  (v) => (v !== null && v !== undefined && v !== "") || 'Enter a value.'
];

const rulesSingleList = [
  (v) => (v !== null && v !== undefined && v !== '') || 'Select a value.',
]

const rulesMultiList = [
  (v) => (Array.isArray(v) && v.length > 0) || 'Select at least one value.'
];

/* ---------------------------
   ACTIONS
---------------------------- */
function emitClose() {
  emit("close");
}

async function submit() {
  if (!(await formRef.value.validate()).valid) return;

  emit("submit", {
    extension: props.extension,
    values: formValues.value
  });
}
</script>
