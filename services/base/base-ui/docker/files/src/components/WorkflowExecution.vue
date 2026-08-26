<template>
  <v-card>
    <v-form v-model="valid" ref="executeWorkflow">
      <v-card-title class="d-flex justify-space-between">
        <h5>Workflow Execution</h5>
        <v-tooltip location="bottom">
          <template v-slot:activator="{ props }">
            <v-btn v-bind="props" @click="getKaapanaInstances()" size="small" icon variant="text">
              <v-icon color="primary">
                mdi-refresh
              </v-icon>
            </v-btn>
          </template>
          <span>refresh Workflow Execution component</span>
        </v-tooltip>
      </v-card-title>
      <v-card-text>
        <v-container>
          <v-row v-if="available_kaapana_instance_names.length > 1">
            <v-icon color="primary" class="mx-2" size="small">mdi-home</v-icon>
            Local instance: {{ localKaapanaInstance }}
          </v-row>
          <v-row v-if="available_kaapana_instance_names.length > 1">
            <v-col cols="12">
              <v-select v-model="selected_kaapana_instance_names" :items="available_kaapana_instance_names"
                label="Runner instances" multiple chips>
                <template #append>
                  <HelpIcon text="On which instances do you want to execute the workflow?" />
                </template>
              </v-select>
            </v-col>
          </v-row>
          <!-- DAG: select dag -->
          <v-row>
            <v-col cols="12" v-if="available_dags.length">
              <v-autocomplete v-if="selected_kaapana_instance_names.length" v-model="dag_id" :items="available_dags"
                label="Workflow" :rules="dagRules()" required>
                <template #append>
                  <HelpIcon text="Workflow to execute" />
                </template>
              </v-autocomplete>
            </v-col>
            <v-col cols="12" class="text-center" v-else>
              <v-progress-circular indeterminate color="primary"></v-progress-circular>
            </v-col>
          </v-row>
          <!-- Workflow name -->
          <v-row v-if="dag_id">
            <v-col cols="12">
              <v-text-field label="Workflow name" v-model="workflow_name" :rules="workflownameRules()"
                required>
                <template #append>
                  <HelpIcon text="Name used to identify this workflow run." />
                </template>
              </v-text-field>
            </v-col>
          </v-row>
          <!-- Data- and Workflow forms -->
          <v-row v-if="datasets_available" :key="dag_id || ''">
            <v-col v-for="(schema, name) in schemas" cols="12" :key="name">
              <a v-if="name === 'documentation_form'" :href="getHref('/docs/' + schema.path)"
                target="_blank">
                <span> Link to the documentation </span>
              </a>
              <Vjsf v-if="name != 'documentation_form'" v-model="formData[name]" :schema="compatSchemas[name]" :options="vjsfOptions"></Vjsf>
            </v-col>
            <!-- Plain Vuetify autocomplete instead of a vjsf field: vjsf builds
                 one node per oneOf branch, so hundreds of datasets blow the
                 render call stack; the autocomplete virtualizes its menu. -->
            <v-col cols="12" v-if="showDatasetPicker" :key="'__dataset_picker__'">
              <v-autocomplete v-model="selectedDataset" :items="datasetItems" item-title="title"
                item-value="value" label="Dataset name (size)" clearable
                no-data-text="No datasets available in this project"
                :rules="datasetRequired ? [(v: any) => !!v || 'Dataset name is required'] : []">
                <template #append>
                  <HelpIcon text="Dataset the workflow runs on; the number in parentheses is its case count." />
                </template>
              </v-autocomplete>
            </v-col>
            <v-col cols="12" v-if="showDatasetLimit" :key="'__dataset_limit__'">
              <div class="d-flex align-center ga-4">
                <v-switch v-model="datasetLimitWhole" label="Process whole dataset" color="primary"
                  hide-details></v-switch>
                <v-number-input v-if="!datasetLimitWhole" v-model="datasetLimit" :min="1"
                  label="Limit dataset size" hide-details></v-number-input>
                <HelpIcon v-if="datasetLimitHelp" :text="datasetLimitHelp" />
              </div>
            </v-col>
            <div v-if="hasBackendField">
              <v-row>
                  <v-card>
                  <v-treeview
                      v-model:selected="selectedItems"
                      :items="treeItems"
                      item-value="path"
                      item-title="name"
                      selectable
                      select-strategy="classic"
                      activatable
                      open-on-click
                      :load-children="fetchChildren"
                  >
                      <template v-slot:prepend="{ item, isOpen }">
                      <v-icon v-if="!(item as TreeItem).file">
                          {{ isOpen ? "mdi-folder-open" : "mdi-folder" }}
                      </v-icon>
                      <v-icon v-else>
                          mdi-file-document-outline
                        </v-icon>
                      </template>
                      <template v-slot:title="{ item }">
                      <span class="text-wrap">{{ (item as TreeItem).name }}</span>
                      </template>
                  </v-treeview>
                  </v-card>
              </v-row>
          </div>
          </v-row>
          <!-- Select remote instance for remote workflow -->
          <v-row v-show="remote_instances_w_external_dag_available.length">
            <v-col cols="12">
              <h3>Remote Workflow</h3>
            </v-col>
            <v-col cols="12">
              <v-select v-model="selected_remote_instances_w_external_dag_available"
                :items="remote_instances_w_external_dag_available" label="External Instance names" multiple chips
                hint="On which (remote) nodes do you want to execute the workflow"></v-select>
            </v-col>
          </v-row>
          <!-- Forms of external workflows -->
          <v-row v-if="Object.keys(external_schemas).length">
            <v-col v-for="(schema, name) in external_schemas" cols="12" :key="name">
              <p>{{ name }}</p>
              <Vjsf v-model="formData['external_schema_' + name]" :schema="compatExternalSchemas[name]" :options="vjsfOptions"></Vjsf>
            </v-col>
          </v-row>
          <!-- Conf data summarizing the configured workflow -->
          <v-row>
            <v-col cols="12">
              <v-tooltip v-model="showConfData" location="top">
                <template v-slot:activator="{ props }">
                  <v-btn icon variant="text" v-bind="props">
                    <v-icon color="#BDBDBD">mdi-email</v-icon>
                  </v-btn>
                </template>
                <pre class="text-left">Workflow name: {{ workflow_name }}</pre>
                <pre class="text-left">Dag id: {{ dag_id }}</pre>
                <pre class="text-left">
            Instance name: {{ selected_kaapana_instance_names }}
          </pre>
                <pre class="text-left">
            External instance name: {{
              selected_remote_instances_w_external_dag_available
            }}
          </pre>
                <pre class="text-left">{{ formDataFormatted }}</pre>
              </v-tooltip>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-card-actions v-if="available_dags.length">
        <v-spacer></v-spacer>
        <v-btn color="primary" variant="elevated" @click="submissionValidator()">
          Start Workflow
        </v-btn>
        <v-btn variant="elevated" @click="isDialog ? cancel() : clearForm()">
          {{ isDialog ? "Cancel" : "Clear" }}
        </v-btn>
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { reactive, toRefs, computed, watch, onMounted, ref } from "vue";
import { notify } from "@kyvg/vue3-notification";
// Explicit Vuetify imports: this component ships pre-compiled, so the host
// app's auto-import/global registration cannot resolve components for it.
// Vuetify stays a peer, so these bind to the consumer's copy.
import {
  VCard, VForm, VCardTitle, VCardText, VCardActions, VContainer, VRow, VCol,
  VIcon, VBtn, VTooltip, VSelect, VAutocomplete, VTextField, VProgressCircular,
  VSwitch, VNumberInput, VTreeview, VSpacer,
} from "vuetify/components";
import { HelpIcon } from "./HelpIcon";
import { postViewDirty } from "../utils/viewDirty";
import kaapanaApiService from "../utils/kaapanaApiService";
import Vjsf from "@koumoul/vjsf";
import { v2compat } from "@koumoul/vjsf/compat/v2";
import "@koumoul/vjsf/styles/vjsf.css";

interface TreeItem {
  name: string;
  path: string;
  file?: boolean;
  children?: TreeItem[];
}

interface State {
  valid: boolean | null;
  localKaapanaInstance: string | Record<string, never>;
  available_kaapana_instance_names: string[];
  selected_kaapana_instance_names: string[];
  selected_remote_instances_w_external_dag_available: string[];
  remote_instances_w_external_dag_available: string[];
  dag_id: string | null;
  available_dags: string[];
  external_dag_id: string | null;
  formData: Record<string, any>;
  schemas: Record<string, any>;
  schemas_dict: Record<string, any>;
  external_schemas: Record<string, any>;
  workflow_name: string | null;
  showConfData: boolean;
  datasets_available: boolean;
  workflowsSettings: Record<string, any>;
  hasBackendField: boolean;
  backendRoute: string | null;
  treeItems: TreeItem[];
  selectedItems: string[];
  datasetItems: { title: string; value: string }[];
  datasetRequired: boolean;
  showDatasetPicker: boolean;
  selectedDataset: string | null;
  showDatasetLimit: boolean;
  datasetLimitWhole: boolean;
  datasetLimit: number;
  datasetLimitHelp: string;
}

const props = withDefaults(
  defineProps<{
    isDialog?: boolean;
    identifiers?: unknown[];
    onlyLocal?: boolean;
    kind_of_dags?: string;
    validDags?: string[];
    reportViewDirty?: boolean;
  }>(),
  {
    isDialog: false,
    identifiers: () => [],
    onlyLocal: false,
    kind_of_dags: "all",
    validDags: () => [],
    // undefined (not false): Vue casts an absent Boolean prop to false, which
    // would defeat the `?? !isDialog` fallback in reportDirty.
    reportViewDirty: undefined,
  }
);

const emit = defineEmits<{
  cancel: [];
  successful: [];
}>();

// Default: the standalone view reports dirty state to the shell, dialog embeds don't.
const reportDirty = computed(() => props.reportViewDirty ?? !props.isDialog);

function initialState(): State {
  return {
    valid: false,
    localKaapanaInstance: {},
    available_kaapana_instance_names: [],
    selected_kaapana_instance_names: [],
    selected_remote_instances_w_external_dag_available: [],
    remote_instances_w_external_dag_available: [],
    dag_id: null,
    available_dags: [],
    external_dag_id: null,
    formData: {},
    schemas: {},
    schemas_dict: {},
    external_schemas: {},
    workflow_name: null,
    showConfData: false,
    datasets_available: true,
    workflowsSettings: {},
    hasBackendField: false,
    backendRoute: null,
    treeItems: [],
    selectedItems: [],
    datasetItems: [],
    datasetRequired: false,
    showDatasetPicker: false,
    selectedDataset: null,
    showDatasetLimit: false,
    datasetLimitWhole: true,
    datasetLimit: 1,
    datasetLimitHelp: "",
  };
}

const state = reactive<State>(initialState());
const {
  valid,
  localKaapanaInstance,
  available_kaapana_instance_names,
  selected_kaapana_instance_names,
  selected_remote_instances_w_external_dag_available,
  remote_instances_w_external_dag_available,
  dag_id,
  available_dags,
  external_dag_id,
  formData,
  schemas,
  schemas_dict,
  external_schemas,
  workflow_name,
  showConfData,
  datasets_available,
  hasBackendField,
  treeItems,
  selectedItems,
  datasetItems,
  datasetRequired,
  showDatasetPicker,
  selectedDataset,
  showDatasetLimit,
  datasetLimitWhole,
  datasetLimit,
  datasetLimitHelp,
} = toRefs(state);

// Outside initialState() so it survives reset(); set fresh on every dag change.
const form_requiredFields = ref<string[]>([]);

// View-dirty reporting: the shell warns before a project switch reloads this
// iframe. Dirty must reflect user input only — a single-dag project re-selects
// its dag on every load (so that choice alone is not dirty), and vjsf fills
// formData with schema defaults asynchronously, so the baseline tracks formData
// until the user first interacts, then freezes.
const userTouchedForm = ref(false);
const formBaseline = ref("{}");

function stableStringify(value: unknown): string {
  return JSON.stringify(value, (_key, val) =>
    val && typeof val === "object" && !Array.isArray(val)
      ? Object.keys(val as object)
          .sort()
          .reduce(
            (acc: Record<string, unknown>, k) => ((acc[k] = (val as Record<string, unknown>)[k]), acc),
            {}
          )
      : val
  );
}

function markFormTouched() {
  userTouchedForm.value = true;
}

watch(
  () => state.formData,
  () => {
    if (!userTouchedForm.value) formBaseline.value = stableStringify(state.formData);
  },
  { deep: true }
);

const viewDirty = computed(() => {
  const dagDirty = state.dag_id !== null && state.available_dags.length > 1;
  const formDirty =
    userTouchedForm.value && stableStringify(state.formData) !== formBaseline.value;
  // Native (non-vjsf) inputs, both reset on every dag change (see dag watcher).
  const nativeDirty = state.selectedDataset !== null || state.datasetLimitWhole === false;
  return dagDirty || formDirty || nativeDirty;
});

watch(viewDirty, (dirty) => {
  if (reportDirty.value) postViewDirty(dirty);
});

const executeWorkflow = ref<VForm | null>(null);

// Kaapana DAG schemas use vjsf-2-era conventions that vjsf 3 / ajv either
// reject (the whole form renders blank) or silently ignore. Normalize in place:
// - boolean `required: true` on a property -> parent-level `required` array
// - value-discriminated `dependencies` -> `allOf` if/then (json-layout gates
//   `dependencies` only on "key is defined", never on its value)
function normalizeV2Schema(fragment: any): any {
  if (!fragment || typeof fragment !== "object" || Array.isArray(fragment)) {
    return fragment;
  }
  // ajv rejects empty `enum`/`oneOf` and crashes the whole form; real DAGs emit
  // them for "nothing to pick yet" fields. Drop the constraint, mark readOnly.
  if (Array.isArray(fragment.enum) && fragment.enum.length === 0) {
    delete fragment.enum;
    fragment.readOnly = true;
  }
  if (Array.isArray(fragment.oneOf) && fragment.oneOf.length === 0) {
    delete fragment.oneOf;
    fragment.readOnly = true;
  }
  if (fragment.properties && typeof fragment.properties === "object") {
    const requiredNames: string[] = [];
    for (const [key, prop] of Object.entries<any>(fragment.properties)) {
      if (prop && typeof prop === "object" && typeof prop.required === "boolean") {
        if (prop.required) requiredNames.push(key);
        delete prop.required;
      }
    }
    if (requiredNames.length) {
      const existing = Array.isArray(fragment.required) ? fragment.required : [];
      fragment.required = [...new Set([...existing, ...requiredNames])];
    }
  }
  // vjsf 2 ignored `type` mismatching object-valued oneOf consts; vjsf 3's ajv
  // enforces both, leaving the field stuck in error. Reconcile `type` to the
  // consts' type, and keep the compact select look by moving `title` to
  // `oneOfLayout.label` (an object-typed node would render as a sub-form).
  if (typeof fragment.type === "string" && Array.isArray(fragment.oneOf) &&
      fragment.oneOf.every((b: any) => b && "const" in b)) {
    const jsType = (v: any) => (Array.isArray(v) ? "array" : v === null ? "null" : typeof v);
    const constTypes = new Set(fragment.oneOf.map((b: any) => jsType(b.const)));
    if (constTypes.size === 1) {
      const t = [...constTypes][0];
      const matches =
        fragment.type === t ||
        (t === "number" && (fragment.type === "integer" || fragment.type === "number"));
      if (!matches) {
        fragment.type = t;
        if (fragment.title) {
          fragment.oneOfLayout = { label: fragment.title };
          delete fragment.title;
        }
      }
    }
  }
  if (fragment.dependencies) {
    for (const [key, dep] of Object.entries<any>(fragment.dependencies)) {
      const isConstDiscriminated =
        dep && typeof dep === "object" && !Array.isArray(dep) && Array.isArray(dep.oneOf) &&
        dep.oneOf.every((b: any) => b && b.properties && b.properties[key] && "const" in b.properties[key]);
      if (!isConstDiscriminated) continue;
      for (const branch of dep.oneOf) {
        const { [key]: trigger, ...extras } = branch.properties;
        if (Object.keys(extras).length === 0) continue;
        const thenSchema: any = { ...branch, properties: extras };
        if (Array.isArray(thenSchema.required)) {
          thenSchema.required = thenSchema.required.filter((k: string) => k !== key);
          if (!thenSchema.required.length) delete thenSchema.required;
        }
        fragment.allOf = fragment.allOf ?? [];
        fragment.allOf.push({
          if: { required: [key], properties: { [key]: { const: trigger.const } } },
          then: thenSchema,
        });
      }
      delete fragment.dependencies[key];
    }
    if (Object.keys(fragment.dependencies).length === 0) delete fragment.dependencies;
  }
  for (const child of Object.values(fragment.properties ?? {})) normalizeV2Schema(child);
  if (fragment.items) {
    if (Array.isArray(fragment.items)) fragment.items.forEach(normalizeV2Schema);
    else normalizeV2Schema(fragment.items);
  }
  for (const kw of ["allOf", "oneOf", "anyOf"]) {
    if (Array.isArray(fragment[kw])) fragment[kw].forEach(normalizeV2Schema);
  }
  for (const dep of Object.values(fragment.dependencies ?? {})) normalizeV2Schema(dep);
  if (fragment.then) normalizeV2Schema(fragment.then);
  if (fragment.else) normalizeV2Schema(fragment.else);
  return fragment;
}

// Adapt to vjsf 3 at render time only: the dag_id watcher and
// processDefaultsFromSettings keep operating on the v2 shape
// (findRequiredFields relies on the boolean `required` convention).
function toVjsfSchema(schema: any) {
  try {
    return v2compat(normalizeV2Schema(JSON.parse(JSON.stringify(schema))));
  } catch (e) {
    console.warn("vjsf v2compat conversion failed; using raw schema", e);
    return schema;
  }
}

// Field descriptions become click-to-reveal help toggles. `hint` is left out
// deliberately: json-layout resolves description as subtitle -> hint -> help,
// so listing it would pre-empt the help toggle.
const vjsfOptions = {
  useDescription: ["subtitle", "help"] as ("hint" | "subtitle" | "help")[],
};

const compatSchemas = computed<Record<string, any>>(() => {
  const out: Record<string, any> = {};
  for (const [name, schema] of Object.entries(state.schemas)) {
    if (name === "documentation_form") continue;
    out[name] = toVjsfSchema(schema);
  }
  return out;
});

const compatExternalSchemas = computed<Record<string, any>>(() => {
  const out: Record<string, any> = {};
  for (const [name, schema] of Object.entries(state.external_schemas)) {
    out[name] = toVjsfSchema(schema);
  }
  return out;
});

const formDataFormatted = computed(() => formatFormData(state.formData));

function getHref(link: string) {
  return link.match(/^:(\d+)(.*)/)
    ? "http://" + window.location.hostname + link
    : link;
}
function reset() {
  Object.assign(state, initialState());
  refreshClient();
  loadWorkflowSettings();
}
function refreshClient() {
  getKaapanaInstances();
}
function loadWorkflowSettings() {
  // The shell seeds localStorage["settings"]; guarded so a view opened outside
  // the shell doesn't throw on JSON.parse(undefined) in onMounted.
  const raw = localStorage["settings"];
  if (!raw) return;
  let settings;
  try {
    settings = JSON.parse(raw);
  } catch {
    return;
  }
  if (settings && settings.hasOwnProperty("workflows")) {
    state.workflowsSettings = settings["workflows"];
  }
}
function clearForm() {
  state.dag_id = null;
}
function cancel() {
  emit("cancel");
  reset();
}
function formatFormData(formData: Record<string, any>) {
  // Only necessary because vjsf does not allow to have same keys in selection form with dependencies
  let formDataFormatted: Record<string, any> = {};
  Object.entries(formData).forEach(([form_key, form_value]) => {
    if (form_key == "workflow_form") {
      formDataFormatted[form_key] = {};
      Object.entries(form_value).forEach(([key, value]) => {
        formDataFormatted[form_key][key.split("#")[0]] = value;
      });
    } else {
      formDataFormatted[form_key] = form_value;
    }
  });
  return formDataFormatted;
}
// The loaders below are fire-and-forget (watchers, tree callbacks), so the
// error has to be reported here — nobody up the stack can.
function notifyLoadError(title: string, error: any) {
  notify({
    type: "error",
    title,
    text: error?.response?.data?.detail ?? error?.message,
  });
}
async function getBackendRootItems() {
  try {
    state.selectedItems = [];
    state.treeItems = [];
    if (!state.backendRoute) {
      console.error("Backend route is not set. Cannot fetch root items.");
      state.treeItems = [];
      return;
    }
    const response: any = await kaapanaApiService.kaapanaApiGet(state.backendRoute);
    if (response && response.data) {
      state.treeItems = response.data;
    } else {
      console.error("Unexpected response format:", response);
      state.treeItems = [];
    }
  } catch (err) {
    notifyLoadError("Failed to load the file browser", err);
  }
}
async function fetchChildren(item: any) {
  if (item.file || (item.children && item.children.length > 0)) {
    return;
  }

  try {
    const response: any = await kaapanaApiService.kaapanaApiGet(state.backendRoute, {
      prefix: item.path,
    });
    item.children = response.data;
  } catch (error) {
    notifyLoadError("Failed to load folder contents", error);
    // Set empty children to avoid repeated failed requests
    item.children = [];
  }
}
/**
 * Set the default value for VJsf schema (workflow form)
 * for the selected dag, if default value is availabe in
 * user settings from local storage
 * Default value in user settings should be under `workflows` key as follows:
 * dagName: {
 *    properties: {
 *            param1Name: 'param1 value',
 *            param2Name: 'param2 Value',
 *        },
 *        hideOnUI: ['param2Name'],  // if param2Name should be hidden on the workflow form in UI
 *    },
 * }
 * all the dag name and param names should be in camelCase in settings. Dag name and parameter name
 * in snakecase/dashcase from airflow backend will be converted in camelCase.
 * e.g. validate-dicoms -> validateDicoms
 */
function processDefaultsFromSettings(schema: Record<string, any>) {
  if (!state.workflow_name) {
    return;
  }

  var workflowName = toCamelCase(state.workflow_name);
  if (!state.workflowsSettings.hasOwnProperty(workflowName)) {
    return;
  }

  var parsedSchema = JSON.parse(JSON.stringify(schema));
  if (parsedSchema.hasOwnProperty("workflow_form")) {
    const props = parsedSchema["workflow_form"]["properties"];
    const wfOptions = state.workflowsSettings[workflowName];
    const defaults = wfOptions["properties"];

    for (const [key, value] of Object.entries(props)) {
      if (defaults.hasOwnProperty(key)) {
        props[key]["default"] = defaults[key];
        // v2compat maps x-display "hidden" to layout "none": not rendered,
        // but the default still reaches the submitted model.
        if (wfOptions.hideOnUI.includes(key)) {
          props[key]["x-display"] = "hidden";
        }
      }
    }

    state.schemas["workflow_form"]["properties"] = props;
  }
}
function dagRules() {
  return [(v: any) => !!v || "Workflow is required"];
}
function workflownameRules() {
  return [(v: any) => !!v || "Workflow name is required"];
}
function findRequiredFields(obj: any, result: string[] = [], prefix = ""): string[] {
  for (const key in obj) {
    const value = obj[key];
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (key === "oneOf") {
      continue;
    }
    if (value && typeof value === "object") {
      findRequiredFields(value, result, fullKey);
    } else if (key === "required") {
      result.push(fullKey);
    }
  }
  return result;
}
function validConfirmation() {
  const formatted = formatFormData(state.formData);
  const failedConfirmations: string[] = [];
  Object.entries(formatted).forEach(([formName, formValue]) => {
    if (
      formValue && typeof formValue === "object"
      && Object.prototype.hasOwnProperty.call(formValue, "confirmation")
    ) {
      const value = formValue.confirmation;
      if (value !== true) {
        failedConfirmations.push(formName);
      }
    }
  });

  return failedConfirmations;
}
async function submissionValidator() {
  let valid_check = [];
  let invalid_fields = [];
  if (state.datasets_available !== true) {
    const message = "The selected runner instances have no common allowed datasets!";
    notify({
      type: "error",
      title: message,
    });
    return false;
  }
  // vuetify field rules first
  const validation = await executeWorkflow.value!.validate();
  if (validation.valid) {
    // then the schema's required fields, which vjsf does not enforce itself
    for (let i = 0; i < form_requiredFields.value.length; i++) {
      const req_field = form_requiredFields.value[i];
      // req_field looks like "<form>.<...>.<prop>.required"
      const substrings = req_field.split(".");
      let form_name = "";
      let req_prop_name = "";
      for (let i = 0; i < substrings.length; i++) {
        if (i === 0) {
          form_name = substrings[i];
        } else if (substrings[i] === "required") {
          req_prop_name = substrings[i - 1];
          break;
        }
      }
      if (state.formData[form_name].hasOwnProperty(req_prop_name)) {
        const fieldValue = state.formData[form_name][req_prop_name];

        // Validate arrays - check if array has at least one non-empty element
        // Validate all others, excluding null and "", but allowing 0 or false
        const isValid = Array.isArray(fieldValue)
          ? fieldValue.length > 0 && fieldValue.some((val) => val && val.trim() !== "")
          : fieldValue !== null && fieldValue !== undefined && fieldValue !== "";

        if (isValid) {
          valid_check.push(true);
        } else {
          valid_check.push(false);
          invalid_fields.push(req_prop_name);
        }
      } else {
        valid_check.push(false);
        invalid_fields.push(req_prop_name);
      }
    }
    if (valid_check.every((value) => value === true)) {
      // confirmations last, only once everything else is OK
      const failedConfirmations = validConfirmation();
      if (failedConfirmations.length > 0) {
        notify({
          type: "error",
          title: "Please accept all required confirmations before starting the workflow.",
          text: `Missing confirmation in: ${failedConfirmations.join(", ")}`,
        });
        return false;
      }
      submitWorkflow();
      return true;
    } else {
      const message = `Validation of form input values failed! Please set required values for ${invalid_fields.join(
        ", "
      )}!`;
      notify({
        type: "error",
        title: message,
      });
      return false;
    }
  } else {
    const message = `Validation of form input values failed! Please set all required values!`;
    notify({
      type: "error",
      title: message,
    });
    return false;
  }
}
function getKaapanaInstances() {
  kaapanaApiService
    .federatedClientApiPost("/get-kaapana-instances")
    .then((response: any) => {
      state.available_kaapana_instance_names = response.data
        .filter((instance: any) => {
          if (props.onlyLocal) {
            return !instance.remote;
          }
          return instance.allowed_dags.length !== 0 || !instance.remote;
        })
        .map(({ instance_name }: any) => instance_name);

      state.localKaapanaInstance = response.data
        .filter((instance: any) => {
          return !instance.remote;
        })
        .map(({ instance_name }: any) => instance_name)[0];
    })
    .catch((err) => {
      notifyLoadError("Failed to load runner instances", err);
    });
}
function getKaapanaInstancesWithExternalDagAvailable() {
  kaapanaApiService
    .federatedClientApiPost("/get-kaapana-instances", {
      dag_id: state.external_dag_id,
    })
    .then((response: any) => {
      state.remote_instances_w_external_dag_available = response.data.map(
        ({ instance_name }: any) => instance_name
      );
      if (state.remote_instances_w_external_dag_available.length === 0) {
        notify({
          title: `No registered remote instance with ${state.external_dag_id} as allowed DAG.`,
          type: "error",
        });
      }
    })
    .catch((err) => {
      notifyLoadError("Failed to load remote runner instances", err);
    });
}
function getDags() {
  kaapanaApiService
    .federatedClientApiPost("/get-dags", {
      instance_names: state.selected_kaapana_instance_names,
      kind_of_dags: props.kind_of_dags,
    })
    .then((response: any) => {
      state.available_dags = response.data;
      if (props.validDags.length > 0) {
        state.available_dags = response.data.filter((item: any) =>
          props.validDags.includes(item)
        );
      }
    })
    .catch((err) => {
      notifyLoadError("Failed to load workflows", err);
    });
}
function getUiFormSchemas() {
  kaapanaApiService
    .federatedClientApiPost("/get-ui-form-schemas", {
      workflow_name: state.workflow_name,
      instance_names: state.selected_kaapana_instance_names,
    })
    .then((response: any) => {
      state.schemas_dict = response.data;
    })
    .catch((err) => {
      notifyLoadError("Failed to load the workflow form", err);
    });
}
function getExternalUiFormSchemas() {
  kaapanaApiService
    .federatedClientApiPost("/get-ui-form-schemas", {
      workflow_name: state.workflow_name,
      dag_id: state.external_dag_id,
      instance_names: state.selected_remote_instances_w_external_dag_available,
    })
    .then((response: any) => {
      state.external_schemas = response.data[state.external_dag_id as string];
    })
    .catch((err) => {
      notifyLoadError("Failed to load the remote workflow form", err);
    });
}
function submitWorkflow() {
  let federated_data = false;
  if (state.selected_remote_instances_w_external_dag_available.length) {
    state.formData["external_schema_instance_names"] =
      state.selected_remote_instances_w_external_dag_available;
    federated_data = true;
  }

  if (props.identifiers.length > 0) {
    state.formData["data_form"] = {
      identifiers: props.identifiers,
    };
  }
  if (state.hasBackendField) {
    state.formData["backend_form"] = {
      selectedFilesAndFolders: state.selectedItems,
    };
  }
  // A failed POST leaves merged keys in data_form; clear them so a retry
  // doesn't carry a stale dataset_name / dataset_limit.
  if (state.formData["data_form"]) {
    delete state.formData["data_form"].dataset_name;
    delete state.formData["data_form"].dataset_limit;
  }
  // merge the native dataset picker / limit inputs back into data_form
  if (state.showDatasetPicker && state.selectedDataset) {
    state.formData["data_form"] = {
      ...(state.formData["data_form"] ?? {}),
      dataset_name: JSON.parse(state.selectedDataset),
    };
  }
  if (state.showDatasetLimit && !state.datasetLimitWhole) {
    // Omit dataset_limit for "whole dataset" — the backend treats missing as no limit.
    state.formData["data_form"] = {
      ...(state.formData["data_form"] ?? {}),
      dataset_limit: state.datasetLimit ?? 1,
    };
  }
  kaapanaApiService
    .federatedClientApiPost("/workflow", {
      workflow_name: state.workflow_name,
      dag_id: state.dag_id,
      instance_names: state.selected_kaapana_instance_names,
      conf_data: formatFormData(state.formData),
      remote: undefined,
      federated: federated_data,
    })
    .then((response: any) => {
      notify({
        type: "success",
        title: "Workflow successfully created!",
      });
      reset();
      // Navigation on success is the consumer's job (via @successful).
      emit("successful");
    })
    .catch((err) => {
      console.log(err);
      notify({
        type: "error",
        title: "An error occured during the workflow creation!",
      });
    });
}
function toCamelCase(target: string) {
  return target.replace(/(-|_)([a-z])/g, function (g) {
    return g[1].toUpperCase();
  });
}

watch(
  () => state.available_kaapana_instance_names,
  (value) => {
    state.selected_kaapana_instance_names = [value[0]];
  }
);
watch(
  () => state.selected_kaapana_instance_names,
  (value) => {
    if (value.length === 0) {
      state.selected_kaapana_instance_names = [
        state.available_kaapana_instance_names[0],
      ];
    }
    getUiFormSchemas();
    getDags();
    state.dag_id = null;
    state.external_dag_id = null;
  }
);
watch(
  () => state.selected_remote_instances_w_external_dag_available,
  () => {
    if (state.selected_remote_instances_w_external_dag_available.length) {
      getExternalUiFormSchemas();
    }
  }
);
watch(
  () => state.available_dags,
  (dagsList) => {
    if (dagsList.length == 1 && state.schemas_dict.hasOwnProperty(dagsList[0])) {
      state.dag_id = dagsList[0];
    }
  }
);
watch(
  () => state.schemas_dict,
  (newDict) => {
    if (
      state.available_dags.length == 1 &&
      newDict.hasOwnProperty(state.available_dags[0])
    ) {
      state.dag_id = state.available_dags[0];
    }
  }
);
watch(
  () => state.dag_id,
  (value) => {
    state.formData = {};
    // Re-arm the dirty baseline for the new dag's form (defaults repopulate async).
    userTouchedForm.value = false;
    state.selectedDataset = null;
    state.showDatasetPicker = false;
    state.datasetItems = [];
    state.datasetRequired = false;
    state.showDatasetLimit = false;
    state.datasetLimitWhole = true;
    state.datasetLimit = 1;
    state.datasetLimitHelp = "";
    // A dag can be selected before its schema arrived; JSON.parse(undefined)
    // would throw here and leave the form permanently blank.
    const rawSchema = value !== null ? state.schemas_dict[value] : null;
    if (value !== null && rawSchema) {
      state.workflow_name = value;
      // deep copy so the original schemas_dict entry stays unmodified
      let schemas = JSON.parse(JSON.stringify(rawSchema));
      if (props.identifiers.length > 0) {
        delete schemas["data_form"];
      }
      if (schemas["backend_form"]) {
        if (!schemas.backend_form["include-dataset"]) {
          delete schemas.data_form;
        }
        state.hasBackendField = true;
        state.backendRoute = schemas.backend_form["backend-route"];
        getBackendRootItems();
      } else {
        state.hasBackendField = false;
      }

      // Lift dataset_name out of the schema into the native autocomplete (see
      // template), before findRequiredFields / state.schemas so vjsf never sees
      // the field; submitWorkflow restores the selection into data_form.
      const dataForm: any = schemas["data_form"];
      const datasetProp: any = dataForm?.properties?.dataset_name;
      if (datasetProp) {
        state.datasetItems = (datasetProp.oneOf ?? []).map((b: any) => ({
          title: b.title ?? "",
          value: JSON.stringify(b.const),
        }));
        state.datasetRequired = datasetProp.required === true;
        state.showDatasetPicker = true;
        delete dataForm.properties.dataset_name;
      }

      // Same lift for dataset_limit (native toggle + number input).
      const limitProp: any = dataForm?.properties?.dataset_limit;
      if (limitProp) {
        state.datasetLimitHelp = limitProp.description ?? "";
        state.showDatasetLimit = true;
        delete dataForm.properties.dataset_limit;
      }

      form_requiredFields.value = findRequiredFields(schemas);
      if ("external_schemas" in schemas) {
        state.external_dag_id = schemas["external_schemas"];
        delete schemas.external_schemas;
      } else {
        state.external_dag_id = null;
      }
      state.schemas = JSON.parse(JSON.stringify(schemas));
    } else {
      state.schemas = {};
      state.external_dag_id = null;
    }
    state.datasets_available = true;
    processDefaultsFromSettings(state.schemas);

    if (state.schemas["data_form"] !== null && state.schemas["data_form"] !== undefined) {
      Object.entries(state.schemas["data_form"]).forEach(([key, value]) => {
        if (key.startsWith("__empty__")) {
          state.datasets_available = false;
          notify({
            type: "error",
            title: "The selected runner instances have no common allowed datasets!",
          });
        }
      });
    }
  }
);
watch(
  () => state.external_dag_id,
  () => {
    state.external_schemas = {};
    if (state.external_dag_id != null) {
      getKaapanaInstancesWithExternalDagAvailable();
    } else {
      state.remote_instances_w_external_dag_available = [];
    }
    Object.entries(state.formData).forEach(([key, value]) => {
      if (
        key.startsWith("external_schema_") &&
        key != "external_schema_federated_form"
      ) {
        console.log(`Deleting ${key}: ${value}`);
        delete state.formData[key];
      }
    });
  }
);
watch(
  () => props.validDags,
  (dags, olddags) => {
    if (dags.length != olddags.length) {
      getDags();
    }
  }
);

onMounted(() => {
  refreshClient();
  loadWorkflowSettings();
  // These events fire only for real user input — vjsf's default population does
  // not. Capture phase so a field's own stopPropagation can't hide them.
  const formEl = executeWorkflow.value?.$el as HTMLElement | undefined;
  if (formEl) {
    (["pointerdown", "keydown", "input", "change"] as const).forEach((evt) =>
      formEl.addEventListener(evt, markFormTouched, true),
    );
  }
});
</script>

<style scoped>
.is-invalid {
  border: 1px solid red;
}

.justify-space-between {
  justify-content: 0;
}

.wfe-help-icon {
  color: #bdbdbd;
}

/* vjsf 3 renders help toggles as a saturated filled circle hanging past the
   field's right edge; tone them down to this view's muted grey and pull them
   back inside the field bounds. */
:deep(.vjsf-help-message-toggle.v-btn) {
  background-color: transparent !important;
  color: #bdbdbd !important;
  box-shadow: none !important;
}
/* !important: vjsf's own `right: -30px` rule ties this one on specificity, so
   without it the winner depends on stylesheet insertion order in the bundle. */
:deep(.vjsf-help-message .vjsf-help-message-toggle) {
  right: 0 !important;
}
</style>
