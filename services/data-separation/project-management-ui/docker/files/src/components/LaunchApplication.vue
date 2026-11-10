<template>
  <v-card>
    <!-- TITLE -->
    <v-card-title v-if="showConfigTitle">
      Configure {{ extension.annotations['ui-visible-name'] }}
    </v-card-title>

    <v-card-text>
      <v-form ref="formRef" class="px-3">
        <template v-for="(param, key) in extensionParams" :key="key">

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



<script setup lang="ts">
import { ref, computed, watch, type PropType } from 'vue'
import type { VForm } from 'vuetify/components'
import { HelpIcon } from '@kaapana/base-ui'

interface ExtensionParam {
  type: string
  default?: unknown
  value?: string[]
  definition?: string
  help?: string
  html?: string
  title?: string
}

interface Extension {
  multiinstallable: string
  name: string
  version: string
  keywords: string[]
  extension_params: Record<string, ExtensionParam> | string | null
  annotations: Record<string, string>
  releaseName: string
}

const props = defineProps({
  busy: { type: Boolean, default: false },
  extension: {
    type: Object as PropType<Extension>,
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
const formRef = ref<InstanceType<typeof VForm> | null>(null)
const formValues = ref<Record<string, any>>({})
const initialValues = ref<Record<string, unknown>>({})

const extensionParams = computed<Record<string, ExtensionParam>>(() => {
  const params = props.extension?.extension_params
  return params && typeof params === 'object' ? params : {}
})

/* ---------------------------
   INITIALIZE PARAM VALUES
---------------------------- */
watch(
  extensionParams,
  (params) => {
    formValues.value = {}
    initialValues.value = {}

    Object.entries(params).forEach(([key, param]) => {
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
  const params = extensionParams.value;
  const firstKey = Object.keys(params)[0];
  if (!firstKey) return false;
  return params[firstKey].type !== "doc";
});

/* ---------------------------
   VALIDATION RULES
---------------------------- */
const rulesStr = [
  (v: unknown) => (v !== null && v !== undefined && v !== "") || 'Enter a value.'
];

const rulesSingleList = [
  (v: unknown) => (v !== null && v !== undefined && v !== '') || 'Select a value.',
]

const rulesMultiList = [
  (v: unknown) => (Array.isArray(v) && v.length > 0) || 'Select at least one value.'
];

/* ---------------------------
   ACTIONS
---------------------------- */
function emitClose() {
  emit("close");
}

async function submit() {
  if (!formRef.value || !(await formRef.value.validate()).valid) return;

  emit("submit", {
    extension: props.extension,
    values: formValues.value
  });
}
</script>
