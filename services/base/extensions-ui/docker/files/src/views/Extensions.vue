<template>
  <div class="workflow-applications">
    <v-container fluid class="text-left">
      <v-card>
        <v-card-title>
          <v-row>
            <v-col cols="12" md="12">
              <span>Applications and workflows &nbsp;
                <v-btn
                  v-if="canUpdateExtensions"
                  data-testid="update-extensions"
                  color="primary"
                  :prepend-icon="kaapanaIcons.refresh"
                  :loading="updatingExtensions"
                  :disabled="updatingExtensions"
                  @click="askUpdateExtensions"
                >
                  Download latest extensions
                </v-btn>
              </span>
            </v-col>
          </v-row>
        </v-card-title>
        <!-- TODO: set max file size limit -->
        <upload
          v-if="canUploadExtensions"
          :label-idle="labelIdle"
          url="/kube-helm-api/filepond-upload"
          :on-process-file-start="fileStart"
          :on-process-file="fileComplete"
          :accepted-file-types="allowedFileTypes"
        />
        <v-card-title>
          <v-row>
            <v-col cols="12" sm="6">
              <v-text-field
                v-model="search"
                :prepend-icon="kaapanaIcons.search"
                label="Search"
                variant="underlined"
                hide-details
              />
            </v-col>
          </v-row>
        </v-card-title>
        <v-data-table
          class="elevation-1"
          :headers="headers"
          :items="filteredLaunchedAppLinks"
          :items-per-page="-1"
          :loading="loading"
          :search="search"
          :sort-by="sortBy"
          loading-text="Waiting a few seconds..."
        >
          <template #header.kind="{ column }">
            {{ column.title }}
            <v-menu>
              <template #activator="{ props }">
                <v-btn icon variant="text" size="small" v-bind="props" data-testid="filter-kind">
                  <v-icon :icon="extensionIcons.filter" />
                </v-btn>
              </template>
              <v-card min-width="200px">
                <v-checkbox v-model="selectedFilters" density="compact" label="Applications" value="Applications" />
                <v-checkbox v-model="selectedFilters" density="compact" label="Workflows" value="Workflows" />
              </v-card>
            </v-menu>
          </template>
          <template #header.experimental="{ column }">
            {{ column.title }}
            <v-menu>
              <template #activator="{ props }">
                <v-btn icon variant="text" size="small" v-bind="props" data-testid="filter-maturity">
                  <v-icon :icon="extensionIcons.filter" />
                </v-btn>
              </template>
              <v-card min-width="200px">
                <v-checkbox v-model="selectedFilters" density="compact" label="Experimental" value="Experimental" />
                <v-checkbox v-model="selectedFilters" density="compact" label="Stable" value="Stable" />
              </v-card>
            </v-menu>
          </template>
          <template #header.resourceRequirement="{ column }">
            {{ column.title }}
            <v-menu>
              <template #activator="{ props }">
                <v-btn icon variant="text" size="small" v-bind="props">
                  <v-icon :icon="extensionIcons.filter" />
                </v-btn>
              </template>
              <v-card min-width="200px">
                <v-checkbox v-model="selectedFilters" density="compact" label="CPU" value="CPU" />
                <v-checkbox v-model="selectedFilters" density="compact" label="GPU" value="GPU" />
              </v-card>
            </v-menu>
          </template>
          <template #item.kind="{ item }">
            <v-tooltip location="bottom" v-if="item.kind === 'dag'">
              <template #activator="{ props }">
                <v-icon color="primary" v-bind="props" :icon="extensionIcons.workflow" />
              </template>
              <span>One or multiple workflows that will trigger Airflow DAGs</span>
            </v-tooltip>
            <v-tooltip location="bottom" v-if="item.kind === 'application'">
              <template #activator="{ props }">
                <v-icon color="primary" v-bind="props" :icon="extensionIcons.application" />
              </template>
              <span>An application with a user interface</span>
            </v-tooltip>
          </template>
          <template #item.uiVisibleName="{ item }">
            <div class="d-flex align-center ga-2">
              <v-tooltip location="bottom" :text="item.description">
                <template #activator="{ props }">
                  <div class="d-flex flex-column" v-bind="props">
                    <span class="text-body-1 font-weight-medium">{{ item.uiVisibleName }}</span>
                    <span class="text-caption text-medium-emphasis text-truncate extensions-description">{{ item.description }}</span>
                  </div>
                </template>
              </v-tooltip>
              <v-tooltip location="bottom" text="Open the documentation in a new tab">
                <template #activator="{ props }">
                  <a
                    :href="getHref('/docs/' + item.documentation)"
                    target="_blank"
                    v-bind="props"
                  >
                    <v-icon color="primary" :icon="kaapanaIcons.help" />
                  </a>
                </template>
              </v-tooltip>
            </div>
          </template>
          <template #item.links="{ item }">
            <a
              v-for="link in item.links"
              :key="link"
              :href="getHref(link)"
              target="_blank"
            >
              <v-icon color="primary" :icon="kaapanaIcons.externalLink" />
            </a>
          </template>
          <template #item.versions="{ item }">
            <v-select
              :items="item.versions"
              v-model="item.version"
              variant="underlined"
              density="compact"
              hide-details
            />
          </template>
          <template #item.resourceRequirement="{ item }">
            <span>{{ item.resourceRequirement.toUpperCase() }}</span>
          </template>
          <template #item.successful="{ item }">
            <v-tooltip
              location="right"
              v-if="item.successful === 'pending'"
              :key="checkDeploymentReady(item)"
            >
              <template #activator="{ props }">
                <v-progress-circular indeterminate color="primary" v-bind="props" />
              </template>
              <span>Helm status: {{ getHelmStatus(item) }} <br /> Kubernetes status: {{ getKubeStatus(item) }}</span>
            </v-tooltip>
            <v-tooltip location="right" v-else-if="item.successful === 'no'">
              <template #activator="{ props }">
                <v-icon color="red" v-bind="props" :icon="kaapanaIcons.error" />
              </template>
              <span>Helm status: {{ getHelmStatus(item) }} <br /> Kubernetes status: {{ getKubeStatus(item) }}</span>
            </v-tooltip>
            <v-tooltip location="right" v-if="checkDeploymentReady(item) === true">
              <template #activator="{ props }">
                <v-icon color="green" v-bind="props" :icon="kaapanaIcons.success" />
              </template>
              <span>Helm status: {{ getHelmStatus(item) }} <br /> Kubernetes status: {{ getKubeStatus(item) }}</span>
            </v-tooltip>
          </template>
          <template #item.experimental="{ item }">
            <v-tooltip location="bottom" v-if="item.experimental === 'yes'">
              <template #activator="{ props }">
                <v-icon color="primary" v-bind="props" :icon="extensionIcons.experimental" />
              </template>
              <span>Experimental extension</span>
            </v-tooltip>
            <v-tooltip location="bottom" v-else>
              <template #activator="{ props }">
                <v-icon color="primary" v-bind="props" :icon="extensionIcons.stable" />
              </template>
              <span>Stable extension</span>
            </v-tooltip>
          </template>
          <template #item.installed="{ item }">
            <v-btn
              v-if="checkInstalled(item) === 'yes' && item.successful !== 'pending' && item.successful !== 'justLaunched'"
              @click="askUninstall(item, false)"
              color="primary"
              min-width="160px"
            >
              <span v-if="item.multiinstallable === 'yes'">Delete</span>
              <span v-if="item.multiinstallable === 'no'">Uninstall</span>
            </v-btn>
            <v-btn
              v-if="checkInstalled(item) === 'no' && item.successful !== 'pending' && item.successful !== 'justLaunched'"
              @click="getFormInfo(item)"
              color="primary"
              min-width="160px"
            >
              <span v-if="item.multiinstallable === 'yes'">Launch</span>
              <span v-if="item.multiinstallable === 'no'">Install</span>

              <v-dialog
                v-if="item.extension_params !== undefined && item.extension_params !== 'null'"
                v-model="popUpDialog[item.releaseName]"
                :retain-focus="false"
                max-width="600px"
                persistent
                scrollable
              >
                <v-card>
                  <v-card-title v-if="popUpItem.extension_params !== undefined && popUpItem.extension_params !== 'null' && Object.keys(popUpItem.extension_params).length > 0 && popUpItem.extension_params[Object.keys(popUpItem.extension_params)[0]].type !== 'doc'">Configure {{ popUpItem.name }}</v-card-title>
                  <v-card-text>
                    <v-form ref="popUpForm" class="px-3">
                      <template v-for="(param, key) in popUpItem.extension_params" :key="key">
                        <div v-if="param.type == 'group_name'" class="text-subtitle-1 font-weight-medium mt-4 mb-2">{{ param.default }}</div>
                        <div v-if="param.type == 'doc'" class="mt-4 mb-2">
                          <div class="text-subtitle-1 font-weight-medium mb-1">{{ param.title }}</div>
                          <div v-if="param.html" class="text-body-2" v-html="param.html"></div>
                        </div>
                        <v-text-field
                          v-if="param.type == 'string'"
                          :label="param.definition ? `${param.definition} (${key}) ` : String(key)"
                          v-model="popUpExtension[key]"
                          clearable
                          :rules="popUpRulesStr"
                        >
                          <template v-if="param.help" #append>
                            <v-tooltip location="right">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" :icon="kaapanaIcons.help" />
                              </template>
                              <div v-html="param.help"></div>
                            </v-tooltip>
                          </template>
                        </v-text-field>
                        <v-checkbox
                          v-if="param.type == 'bool' || param.type == 'boolean'"
                          :label="param.definition ? `${param.definition} (${key}) ` : String(key)"
                          v-model="popUpExtension[key]"
                        >
                          <template v-if="param.help" #append>
                            <v-tooltip location="right">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" :icon="kaapanaIcons.help" />
                              </template>
                              <div v-html="param.help"></div>
                            </v-tooltip>
                          </template>
                        </v-checkbox>
                        <v-select
                          v-if="param.type == 'list_single'"
                          :items="param.value"
                          :label="param.definition ? `${param.definition} (${key}) ` : String(key)"
                          v-model="popUpExtension[key]"
                          :rules="popUpRulesSingleList"
                          clearable
                        >
                          <template v-if="param.help" #append>
                            <v-tooltip location="right">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" :icon="kaapanaIcons.help" />
                              </template>
                              <div v-html="param.help"></div>
                            </v-tooltip>
                          </template>
                        </v-select>
                        <v-select
                          v-if="param.type == 'list_multi'"
                          multiple
                          :items="param.value"
                          :item-title="param.default"
                          :label="param.definition ? `${param.definition} (${key}) ` : String(key)"
                          v-model="popUpExtension[key]"
                          :rules="popUpRulesMultiList"
                          clearable
                        >
                          <template v-if="param.help" #append>
                            <v-tooltip location="right">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" :icon="kaapanaIcons.help" />
                              </template>
                              <div v-html="param.help"></div>
                            </v-tooltip>
                          </template>
                        </v-select>
                      </template>
                    </v-form>
                  </v-card-text>
                  <v-card-actions>
                    <v-spacer />
                    <v-btn color="error" @click="resetFormInfo(item.releaseName)">Abort</v-btn>
                    <v-btn color="primary" v-if="item.multiinstallable === 'no'" @click="submitForm(item.releaseName)">Install</v-btn>
                    <v-btn color="primary" v-if="item.multiinstallable === 'yes'" @click="submitForm(item.releaseName)">Launch</v-btn>
                  </v-card-actions>
                </v-card>
              </v-dialog>
            </v-btn>

            <v-btn
              v-if="item.successful === 'justLaunched'"
              color="primary"
              min-width="160px"
              disabled
            >
              <span>Launched</span>
            </v-btn>
            <v-menu
              v-if="item.successful === 'pending'"
              v-model="pendingMenu[item.releaseName]"
              :close-on-content-click="false"
            >
              <template #activator="{ props }">
                <v-btn color="primary" min-width="160px" v-bind="props" :append-icon="kaapanaIcons.expand">
                  Pending
                </v-btn>
              </template>
              <v-card max-width="320px" class="text-left">
                <v-card-title class="text-subtitle-1">Stuck in Pending?</v-card-title>
                <v-card-text class="text-body-2">
                  An installation that stays pending usually means an error in the Helm chart. Forcing
                  the uninstall skips the chart's hooks and clears the release.
                </v-card-text>
                <v-card-actions>
                  <v-spacer />
                  <v-btn color="error" :prepend-icon="kaapanaIcons.delete" @click="askUninstall(item, true)">
                    {{ item.multiinstallable === 'yes' ? 'Force Delete' : 'Force Uninstall' }}
                  </v-btn>
                </v-card-actions>
              </v-card>
            </v-menu>
          </template>
        </v-data-table>
      </v-card>
    </v-container>

    <ConfirmDialog
      v-model="confirmOpen"
      :color="confirmContent.color"
      :title="confirmContent.title"
      :text="confirmContent.text"
      :confirm-text="confirmContent.confirmText"
      @confirm="runPendingAction"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useNotification } from "@kyvg/vue3-notification";
import { ConfirmDialog, kaapanaApiService, refreshShell } from "@kaapana/base-ui";
import Upload from "@/components/Upload.vue";
import { usePolicyStore } from "@/stores/policy";
import { useAuthStore, useProjectStore } from "@kaapana/base-ui";
import { checkAuthR } from "@/utils/opa";
import { extensionIcons, kaapanaIcons } from "@/utils/extensionIcons";
import {
  checkDeploymentReady,
  checkInstalled,
  getHelmStatus,
  getHref,
  getKubeStatus,
  hasReadyDeployment,
} from "@/utils/extensionState";

interface DataTableHeader {
  title: string;
  key: string;
  align?: "start" | "center" | "end";
}

const { notify } = useNotification();
const policyStore = usePolicyStore();
const authStore = useAuthStore();

// The shipped policy grants these kube-helm endpoints to admins only and their
// catch bodies are silent, so the controls are HIDDEN rather than disabled — a
// permission the user can never acquire is not a transient state worth showing.
// authStore.currentUser is {} until checkAuth resolves; read roles defensively.
const allowed = (path: string) =>
  checkAuthR(policyStore.policyData, path, {
    roles: authStore.currentUser?.roles ?? [],
  });
const canUpdateExtensions = computed(() =>
  allowed("/kube-helm-api/update-extensions"),
);
// One control, two endpoints: the drop zone POSTs to filepond-upload, and a
// completed .tar additionally calls import-container (see fileComplete), so it
// needs both.
const canUploadExtensions = computed(
  () =>
    allowed("/kube-helm-api/filepond-upload") &&
    allowed("/kube-helm-api/import-container"),
);

// Resolves the project from the /project/<short_id> document prefix (see base-ui).
useProjectStore()
  .getSelectedProject()
  .catch((err: any) => {
    notify({
      type: "error",
      title: "Project unavailable",
      text: `Could not load the current project. ${err?.response?.data?.detail ?? err?.message}`,
    });
  });

const allowedFileTypes = [
  "application/x-compressed",
  "application/x-tar",
  "application/gzip",
  "application/x-compressed-tar",
];
const loading = ref(true);
const updatingExtensions = ref(false);
const pendingMenu = ref<Record<string, boolean>>({});
let polling = 0;
let pollErrorNotified = false;
let previousReadyReleases: string | null = null;
const launchedAppLinks = ref<any[] | null>([]);
const search = ref("");
const selectedFilters = ref<string[]>(["Stable", "Applications", "Workflows", "GPU", "CPU"]);
const popUpDialog = ref<Record<string, boolean>>({});
const popUpItem = ref<any>({});
const popUpExtension = ref<Record<string, any>>({});
const popUpForm = ref<any>(null);
const popUpRulesStr = [(v: any) => (v && v.length > 0) || "Empty string field"];
const popUpRulesSingleList = [
  (v: any) => (v && v.length > 0) || "Empty single-selectable list field",
];
const popUpRulesMultiList = [
  (v: any) => v.length > 0 || "Empty multi-selectable list field",
];
const labelIdle = "Upload chart (.tgz) or container (.tar) files";
const sortBy = [{ key: "uiVisibleName", order: "asc" as const }];

const headers: DataTableHeader[] = [
  { title: "Type", align: "center", key: "kind" },
  { title: "Name", align: "start", key: "uiVisibleName" },
  { title: "Version", align: "start", key: "versions" },
  { title: "Maturity", align: "center", key: "experimental" },
  { title: "Hardware requirement", align: "start", key: "resourceRequirement" },
  { title: "Action", align: "center", key: "installed" },
  { title: "Ready", align: "center", key: "successful" },
  { title: "Links", align: "center", key: "links" },
];

const filteredLaunchedAppLinks = computed<any[]>(() => {
  if (launchedAppLinks.value !== null) {
    return launchedAppLinks.value.filter((i: any) => {
      let devFilter = false;
      let kindFilter = false;
      let resourceFilter = false;

      if (selectedFilters.value.includes("Experimental") && i.experimental === "yes") {
        devFilter = true;
      } else if (selectedFilters.value.includes("Stable") && i.experimental === "no") {
        devFilter = true;
      }

      if (selectedFilters.value.includes("Applications") && i.kind === "application") {
        kindFilter = true;
      } else if (selectedFilters.value.includes("Workflows") && i.kind === "dag") {
        kindFilter = true;
      }

      if (selectedFilters.value.includes("CPU") && i.resourceRequirement == "cpu") {
        resourceFilter = true;
      } else if (
        selectedFilters.value.includes("GPU") &&
        i.resourceRequirement == "gpu"
      ) {
        resourceFilter = true;
      }

      return devFilter && kindFilter && resourceFilter;
    });
  } else {
    loading.value = true;
    return [];
  }
});

function fileStart(file: any) {
  console.log("filestart", file);
}
// FilePond reports an upload failure inline on the file itself, so only the
// follow-up import of a container image needs feedback from here.
function fileComplete(error: any, file: any) {
  if (error !== null) {
    console.log("filepond file upload error", error);
    return;
  }
  console.log("successfully uploaded file", file);
  const fname = file.filename;
  if (file.fileExtension !== "tar") return;

  console.log("importing container...");
  kaapanaApiService
    .helmApiGet("/import-container", { filename: fname }, 120000)
    .then((response: any) => {
      console.log(response.data);
    })
    .catch((err: any) => {
      notify({
        type: "error",
        title: "Import failed",
        text: `Import of ${fname} failed. ${err?.response?.data?.detail ?? err?.message}`,
      });
    });
}
function getHelmCharts() {
  let params = {
    repo: "kaapana-public",
  };
  kaapanaApiService
    .helmApiGet("/extensions", params)
    .then((response: any) => {
      // Remember a version the user picked in the per-row dropdown so the 5s
      // poll's wholesale array replacement below does not reset it — Install and
      // deleteChart keep operating on the version the user actually sees.
      const previousVersions = new Map<string, any>();
      if (Array.isArray(launchedAppLinks.value)) {
        for (const row of launchedAppLinks.value as any[]) {
          previousVersions.set(row.releaseName, row.version);
        }
      }
      launchedAppLinks.value = response.data;
      launchedAppLinks.value = (launchedAppLinks.value as any[]).map((item: any) => ({
        documentation: item.annotations?.documentation ?? null,
        ...item,
      }));
      // "-" is the backend's placeholder for an unset display_name.
      launchedAppLinks.value = (launchedAppLinks.value as any[]).map((item: any) => ({
        uiVisibleName: (item["display_name"] && item["display_name"].trim() !== "" && item["display_name"].trim() !== "-")
          ? item["display_name"]
          : item.annotations?.["ui-visible-name"] ?? item.releaseName,
        ...item,
      }));
      launchedAppLinks.value = (launchedAppLinks.value as any[]).map((item: any) => {
        const selected = previousVersions.get(item.releaseName);
        return selected && item.versions?.includes(selected)
          ? { ...item, version: selected }
          : item;
      });
      if (launchedAppLinks.value !== null) {
        loading.value = false;
      }
      // A release that just became ready has registered its ingress, so the
      // shell has a menu entry to pick up.
      const ready = (launchedAppLinks.value as any[])
        .filter((item: any) => hasReadyDeployment(item))
        .map((item: any) => item.releaseName)
        .sort()
        .join(",");
      if (previousReadyReleases !== null && ready !== previousReadyReleases) {
        refreshShell();
      }
      previousReadyReleases = ready;
      // Re-arm last: a throw while processing the payload lands in .catch and
      // must not toast again every tick.
      pollErrorNotified = false;
    })
    .catch((err: any) => {
      loading.value = false;
      console.log(err);
      // Polled every 5s, so notify once and re-arm only after a success —
      // otherwise a revoked kaapana.ai/applications claim toasts every tick.
      if (pollErrorNotified) return;
      pollErrorNotified = true;
      notify({
        type: "error",
        title: "Failed to load extensions",
        text: "Could not load the list of extensions. Please try again later.",
      });
    });
}
function startExtensionsInterval() {
  polling = window.setInterval(() => {
    getHelmCharts();
  }, 5000);
}
function clearExtensionsInterval() {
  window.clearInterval(polling);
}
function restartExtensionsInterval() {
  clearExtensionsInterval();
  startExtensionsInterval();
}
function updateExtensions() {
  updatingExtensions.value = true;
  restartExtensionsInterval();
  kaapanaApiService
    .helmApiGet("/update-extensions", {})
    .then((response: any) => {
      console.log(response.data);
    })
    .catch((err: any) => {
      console.log(err);
      notify({
        type: "error",
        title: "Refresh failed",
        text: `Could not refresh the extension list. ${err?.response?.data?.detail ?? err?.message}`,
      });
    })
    .finally(() => {
      updatingExtensions.value = false;
    });
}

/* -------------------------------------------------------- confirmations --- */

type PendingAction =
  | { kind: "uninstall"; item: any; force: boolean }
  | { kind: "update-extensions" };

// Kept after the dialog closes so its content does not blank out during the
// leave transition; the next ask replaces it.
const pendingAction = ref<PendingAction | null>(null);
const confirmOpen = ref(false);

function askUninstall(item: any, force: boolean) {
  pendingMenu.value[item.releaseName] = false;
  pendingAction.value = { kind: "uninstall", item, force };
  confirmOpen.value = true;
}

function askUpdateExtensions() {
  pendingAction.value = { kind: "update-extensions" };
  confirmOpen.value = true;
}

function runPendingAction() {
  const action = pendingAction.value;
  if (!action) return;
  if (action.kind === "update-extensions") {
    updateExtensions();
    return;
  }
  deleteChart(action.item, action.force ? "--no-hooks" : "");
}

// Each text states what happens, what is affected and what follows. `error` for
// the destructive uninstall, `primary` for the download, which is expensive but
// reversible.
const confirmContent = computed(() => {
  const action = pendingAction.value;

  if (action?.kind === "update-extensions") {
    return {
      color: "primary",
      title: "Download the latest extensions?",
      text:
        "Kaapana pulls the current chart catalogue from the configured Helm repository. " +
        "This can take several minutes and use significant network bandwidth and disk space on the platform. " +
        "Extensions that are already installed keep running; only the list of available versions changes.",
      confirmText: "Download",
    };
  }

  if (action?.kind === "uninstall") {
    const { item, force } = action;
    const noun = item.multiinstallable === "yes" ? "instance" : "extension";
    const verb = item.multiinstallable === "yes" ? "Delete" : "Uninstall";

    if (force) {
      return {
        color: "error",
        title: `Force ${verb.toLowerCase()} "${item.uiVisibleName}"?`,
        text:
          `The release ${item.releaseName} (version ${item.version}) is removed with Helm's hooks skipped. ` +
          "Because the chart's cleanup hooks do not run, resources it would normally remove may be left behind in the cluster. " +
          "Use this only for an installation that is genuinely stuck in Pending.",
        confirmText: `Force ${verb.toLowerCase()} ${noun}`,
      };
    }

    return {
      color: "error",
      title: `${verb} "${item.uiVisibleName}"?`,
      text:
        `The release ${item.releaseName} (version ${item.version}) is removed from this project. ` +
        `Containers running for this ${noun} are stopped, and anything stored only inside them is lost. ` +
        "The extension stays in the catalogue and can be installed again later.",
      confirmText: `${verb} ${noun}`,
    };
  }

  return {
    color: "error",
    title: "",
    text: "",
    confirmText: "Confirm",
  };
});
function deleteChart(item: any, helmCommandAddons: any = "") {
  let params = {
    release_name: item.releaseName,
    release_version: item.version,
    helm_command_addons: helmCommandAddons,
  };
  console.log("params", params);
  loading.value = true;
  clearExtensionsInterval();
  startExtensionsInterval();
  kaapanaApiService
    .helmApiPost("/helm-delete-chart", params)
    .then((response: any) => {
      console.log("helm delete response", response);
      item.installed = "no";
      item.successful = "pending";
    })
    .catch((err: any) => {
      console.log("helm delete error", err);
      loading.value = false;
      notify({
        type: "error",
        title: "Uninstall failed",
        text: `Could not uninstall ${item.releaseName}. ${err?.response?.data?.detail ?? err?.message}`,
      });
    });
}

function resetFormInfo(key: any) {
  popUpDialog.value[key] = false;
  if (popUpForm.value) {
    popUpExtension.value = {};
    popUpForm.value.reset();
  }
}

function getFormInfo(item: any) {
  popUpDialog.value[item.releaseName] = false;
  popUpItem.value = {};
  // Reset the params buffer so one install's parameters cannot leak into the next.
  popUpExtension.value = {};

  const params = item["extension_params"];
  // The backend reports a param-less extension as the literal string "null";
  // no config form then — install directly.
  if (params && params !== "null" && Object.keys(params).length > 0) {
    popUpDialog.value[item.releaseName] = true;
    popUpItem.value = item;
    for (let key of Object.keys(params)) {
      popUpExtension.value[key] = params[key]["default"];
    }
  } else {
    installChart(item);
  }
}

async function submitForm(key: any) {
  const result = await popUpForm.value?.validate();
  if (result?.valid) {
    popUpDialog.value[key] = false;
    installChart(popUpItem.value);
  }
}

function addExtensionParams(payload: any) {
  let params = JSON.parse(JSON.stringify(popUpExtension.value));
  console.log("add parameters", params);

  let res = {} as any;
  for (let key of Object.keys(params)) {
    let v = params[key];
    let s = "" as string;
    // TODO: if more types like Object etc will exist as well, check them here
    if (Array.isArray(v) && v.length > 0) {
      for (let vv of v) {
        s += String(vv) + ",";
      }
      s = s.slice(0, s.length - 1);
    } else {
      s = v;
    }

    res[key] = s;
  }
  payload["extension_params"] = res;
  return payload;
}

function installChart(item: any) {
  let payload = {
    name: item.name,
    version: item.version,
    keywords: item.keywords,
  } as any;

  console.log("payload", payload);
  if (Object.keys(popUpExtension.value).length > 0) {
    payload = addExtensionParams(payload);
  }

  loading.value = true;
  clearExtensionsInterval();
  startExtensionsInterval();
  kaapanaApiService
    .helmApiPost("/helm-install-chart", payload)
    .then((response: any) => {
      console.log("helm install response", response);
      item.installed = "yes";
      if (item.multiinstallable === "yes") {
        item.successful = "justLaunched";
      } else {
        item.successful = "pending";
      }
    })
    .catch((err: any) => {
      console.log("helm install error", err);
      loading.value = false;
      notify({
        type: "error",
        title: "Installation failed",
        text: `Installation of ${item.name} failed. ${err?.response?.data?.detail ?? err?.message}`,
      });
    });
}

onMounted(() => {
  getHelmCharts();
  startExtensionsInterval();
});

onBeforeUnmount(() => {
  clearExtensionsInterval();
});
</script>

<style lang="scss">
a {
  text-decoration: none;
}

.extensions-description {
  max-width: 24ch;
}
</style>
