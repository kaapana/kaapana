<template lang="pug">
.workflow-applications
  IdleTracker
  v-container(grid-list-lg, text-left, fluid)
    v-card
      v-card-title
        v-row
          v-col(cols="12", md="12")
            span Applications and workflows &nbsp;
              v-tooltip(bottom="")
                template(v-slot:activator="{ on, attrs }")
                  v-icon(
                    @click="updateExtensions()",
                    color="primary",
                    dark="",
                    v-bind="attrs",
                    v-on="on"
                  ) mdi-cloud-refresh-outline
                span Click to download latest extensions, this might take some time.
      //- TODO: set max file size limit
      upload(:labelIdle="labelIdle", url="/kube-helm-api/filepond-upload", :onProcessFileStart="fileStart", :onProcessFile="fileComplete", :acceptedFileTypes="allowedFileTypes")
      v-card-title
        v-row
          v-col(cols="12", sm="6")
            v-text-field(
              v-model="search",
              prepend-icon="mdi-magnify",
              label="Search",
              hide-details=""
            )
      v-data-table.elevation-1(
        :headers="headers",
        :items="filteredLaunchedAppLinks",
        :items-per-page="20",
        :loading="loading",
        :search="search",
        sort-by="releaseName",
        loading-text="Waiting a few seconds...",
        calculate-widths=true
      )
        template(v-slot:header.kind="{ header }") {{ header.text }}
          v-menu(offset-y)
            template( v-slot:activator="{ on, attrs }")
              v-btn( icon v-bind="attrs" v-on="on")
                v-icon mdi-filter
            v-card(min-width="200px")
              v-checkbox(
                v-model="selectedFilters"
                dense=true
                label="Applications"
                value="Applications")
              v-checkbox(
                v-model="selectedFilters"
                dense=true
                label="Workflows"
                value="Workflows")
        template(v-slot:header.experimental="{ header }") {{ header.text }}
          v-menu(offset-y)
            template( v-slot:activator="{ on, attrs }")
              v-btn( icon v-bind="attrs" v-on="on")
                v-icon mdi-filter
            v-card(min-width="200px")
              v-checkbox(
                v-model="selectedFilters"
                dense=true
                label="Experimental"
                value="Experimental")
              v-checkbox(
                v-model="selectedFilters"
                dense=true
                label="Stable"
                value="Stable")
        template(v-slot:header.resourceRequirement="{ header }") {{ header.text }}
          v-menu(offset-y)
            template( v-slot:activator="{ on, attrs }")
              v-btn( icon v-bind="attrs" v-on="on")
                v-icon mdi-filter
            v-card(min-width="200px")
              v-checkbox(
                v-model="selectedFilters"
                dense=true
                label="CPU"
                value="CPU")
              v-checkbox(
                v-model="selectedFilters"
                dense=true
                label="GPU"
                value="GPU")
        template(v-slot:item.kind="{ item }")
          v-tooltip(bottom="", v-if="item.kind === 'dag'")
            template(v-slot:activator="{ on, attrs }")
              v-icon(color="primary", dark="", v-bind="attrs", v-on="on")
                | mdi-gamepad-variant
            span One or multiple workflows that will trigger Airflow DAGs
          v-tooltip(bottom="", v-if="item.kind === 'application'")
            template(v-slot:activator="{ on, attrs }")
              v-icon(color="primary", dark="", v-bind="attrs", v-on="on")
                | mdi-application-outline
            span An application with a user interface
        template(v-slot:item.releaseName="{ item }")
          div(class="cell-content")
            v-tooltip(bottom)
              template(v-slot:activator="{ on, attrs }")
                div(
                  class="text-content",
                  v-bind="attrs", 
                  v-on="on")
                  span(class="first-line") {{ item.releaseName }}
                  span(class="second-line") {{ item.description.length > 32 ? item.description.slice(0, 32) + "..." : item.description }}
              span {{ item.description }}
            v-tooltip(bottom)
              template(v-slot:activator="{ on, attrs }")
                a(
                  :href="getHref('/docs/' + item.documentation)",
                  target="_blank",
                )
                  v-icon(class="cell-icon", color="primary", dark="", v-bind="attrs", v-on="on") mdi-information
              span Link to the documentation.
        template(v-slot:item.links="{ item }")
          a(
            :href="getHref(link)",
            target="_blank",
            v-for="link in item.links",
            :key="item.link"
          )
            v-icon(color="primary") mdi-open-in-new
        template(v-slot:item.versions="{ item }") 
          v-select(
            :items="item.versions",
            v-model="item.version",
            hide-details="",
          )
        template(v-slot:item.resourceRequirement="{ item }") 
          span {{ item.resourceRequirement.toUpperCase() }}
        template(v-slot:item.successful="{ item }")
          v-tooltip(
            right, 
            v-if="item.successful === 'pending'"
            :key="checkDeploymentReady(item)"
            )
            template(v-slot:activator="{ on, attrs }")
              v-progress-circular(
                  indeterminate,
                  color="primary",
                  v-bind="attrs", 
                  v-on="on"
                )          
            span Helm status: {{ getHelmStatus(item) }} <br /> Kubernetes status: {{ getKubeStatus(item) }}
          v-tooltip(
            right, 
            v-else-if="item.successful === 'no'")
            template(v-slot:activator="{ on, attrs }")
              v-icon(
                color="red", 
                v-bind="attrs", 
                v-on="on"
                ) mdi-alert-circle
            span Helm status: {{ getHelmStatus(item) }} <br /> Kubernetes status: {{ getKubeStatus(item) }}
          v-tooltip(
            right,
            v-if="checkDeploymentReady(item) === true")
            template(v-slot:activator="{ on, attrs }")
              v-icon(
                color="green", 
                v-bind="attrs", 
                v-on="on"
                ) mdi-check-circle
            span Helm status: {{ getHelmStatus(item) }} <br /> Kubernetes status: {{ getKubeStatus(item) }}
          
        template(v-slot:item.experimental="{ item }")
          v-tooltip(bottom="", v-if="item.experimental === 'yes'")
            template(v-slot:activator="{ on, attrs }")
              v-icon(color="primary", dark="", v-bind="attrs", v-on="on")
                | mdi-test-tube
            span Experimental extension
          v-tooltip(bottom="", v-else)
            template(v-slot:activator="{ on, attrs }")
              v-icon(color="primary", dark="", v-bind="attrs", v-on="on")
                | mdi-check-decagram
            span Stable extension
        template(v-slot:item.installed="{ item }")
          v-btn(
            @click="deleteChart(item)",
            color="primary",
            min-width = "160px",
            v-if="checkInstalled(item) === 'yes' && item.successful !== 'pending' && item.successful !== 'justLaunched'"
          ) 
            span(v-if="item.multiinstallable === 'yes'") Delete
            span(v-if="item.multiinstallable === 'no'") Uninstall
          v-btn(
            @click="getFormInfo(item)",
            color="primary",
            min-width = "160px",
            v-if="checkInstalled(item) === 'no' && item.successful !== 'pending' && item.successful !== 'justLaunched'"
          ) 
            span(v-if="item.multiinstallable === 'yes'") Launch
            span(v-if="item.multiinstallable === 'no'") Install

            v-dialog(
              v-if="item.extension_params !== undefined && item.extension_params !== 'null'"
              v-model="popUpDialog[item.releaseName]"
              :retain-focus="false"
              max-width="600px"
              persistent
              scrollable
            )
              v-card
                v-card-title(v-if="popUpItem.extension_params !== undefined && popUpItem.extension_params !== 'null' && Object.keys(popUpItem.extension_params).length > 0 && popUpItem.extension_params[Object.keys(popUpItem.extension_params)[0]].type !== 'doc'") Configure {{ popUpItem.name }}
                v-card-text
                  v-form.px-3(ref="popUpForm")
                    template(v-for="(param, key) in popUpItem.extension_params")
                      span(v-if="param.type == 'group_name'" style="font-weight:bold;font-size:25px;align:left") {{ param.default }}
                      div(v-if="param.type == 'doc'")
                        br
                        span(style="font-weight:bold;font-size:25px;align:left") {{ param.title }}
                        div(v-if="param.html")
                          div(v-html="param.html")
                      v-text-field(
                        v-if="param.type == 'string'"
                        :label="param.definition ? `${param.definition} (${key}) ` : key"
                        v-model="popUpExtension[key]"
                        clearable,
                        :rules="popUpRulesStr"
                      )
                        template(v-if="param.help" v-slot:append-outer)
                          v-tooltip(right)
                            template(v-slot:activator="{ on, attrs }")
                              v-icon(v-bind="attrs" v-on="on") mdi-tooltip-question
                            div(v-html="param.help")
                      v-checkbox(
                        v-if="param.type == 'bool' || param.type == 'boolean'"
                        :label="param.definition ? `${param.definition} (${key}) ` : key"
                        v-model="popUpExtension[key]"
                      )
                        template(v-if="param.help" v-slot:append)
                          v-tooltip(right)
                            template(v-slot:activator="{ on, attrs }")
                              v-icon(v-bind="attrs" v-on="on") mdi-tooltip-question
                            div(v-html="param.help")
                      v-select(
                        v-if="param.type == 'list_single'"
                        :items="param.value"
                        :label="param.definition ? `${param.definition} (${key}) ` : key"
                        v-model="popUpExtension[key]"
                        :rules="popUpRulesSingleList"
                        clearable
                      )
                        template(v-if="param.help" v-slot:append-outer)
                          v-tooltip(right)
                            template(v-slot:activator="{ on, attrs }")
                              v-icon(v-bind="attrs" v-on="on") mdi-tooltip-question
                            div(v-html="param.help")
                      v-select(
                        v-if="param.type == 'list_multi'"
                        multiple
                        :items="param.value"
                        :item-text="param.default"
                        :label="param.definition ? `${param.definition} (${key}) ` : key"
                        v-model="popUpExtension[key]"
                        :rules="popUpRulesMultiList"
                        clearable
                      )
                        template(v-if="param.help" v-slot:append-outer)
                          v-tooltip(right)
                            template(v-slot:activator="{ on, attrs }")
                              v-icon(v-bind="attrs" v-on="on") mdi-tooltip-question
                            div(v-html="param.help")

                      v-file-input(
                        v-if="param.type == 'file_upload'"
                        :label="param.definition ? `${param.definition} (${key}) ` : key"
                        v-model="popUpExtension[key]"
                        clearable
                        accept=".json"
                        @change="(event) => handleFileUpload(event, key)"
                      )
                        template(v-if="param.help" v-slot:append-outer)
                          v-tooltip(right)
                            template(v-slot:activator="{ on, attrs }")
                              v-icon(v-bind="attrs" v-on="on") mdi-tooltip-question
                            div(v-html="param.help")

                v-card-actions
                  v-spacer
                  v-btn(color="error", @click="resetFormInfo(item.releaseName)") Abort
                  v-btn(color="primary", v-if="item.multiinstallable === 'no'" @click="submitForm(item.releaseName)") Install
                  v-btn(color="primary", v-if="item.multiinstallable === 'yes'" @click="submitForm(item.releaseName)") Launch

          v-btn(
            color="primary",
            min-width = "160px",
            disabled=true,
            v-if="item.successful === 'justLaunched'"
          ) 
            span() Launched
          v-menu(:close-on-content-click='false' v-if="item.successful === 'pending'")
            template(v-slot:activator='{ on, attrs }')
              v-btn(color="primary", min-width="160px", v-bind='attrs' v-on='on')
                | Pending
                v-icon mdi-chevron-down
            v-card(max-width="300px" text-left)
              v-card-title Pending states
              v-card-text In case your installation gets stuck in the "pending" state there is most probably something wrong with the helm chart. In that case you can here force to delete/uninstall the extension.
              v-card-actions
                v-btn(
                  @click="deleteChart(item, helmCommandAddons='--no-hooks');",
                  color="primary",
                  min-width="160px",
                ) 
                  span(v-if="item.multiinstallable === 'yes'") Delete forcefully
                  span(v-if="item.multiinstallable === 'no'") Uninstall forcefully
</template>

<script lang="ts">
import Vue from "vue";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";
import Upload from "@/components/Upload.vue";
import IdleTracker from "@/components/IdleTracker.vue";



export default Vue.extend({
  components: {
    Upload,
    IdleTracker,
  },
  data: () => ({
    file: "" as any,
    fileResponse: "",
    dragging: false,
    loadingFile: false,
    allowedFileTypes: [
      "application/x-compressed",
      "application/x-tar",
      "application/gzip",
      "application/x-compressed-tar",
    ],
    conn: null as WebSocket | null,
    loading: true,
    polling: 0,
    launchedAppLinks: [] as any,
    search: "",
    selectedFilters: [
      "Experimental",
      "Stable",
      "Applications",
      "Workflows",
      "GPU",
      "CPU",
    ],
    extensionFilter: [0, 1, 2, 3, 4, 5],
    popUpDialog: {} as any,
    popUpItem: {} as any,
    popUpChartName: "",
    popUpExtension: {} as any,
    popUpRulesStr: [(v: any) => (v && v.length > 0) || "Empty string field"],
    popUpRulesSingleList: [
      (v: any) => (v && v.length > 0) || "Empty single-selectable list field",
    ],
    popUpRulesMultiList: [
      (v: any) => v.length > 0 || "Empty multi-selectable list field",
    ],
    headers: [
      {
        text: "Type",
        align: "center",
        value: "kind",
      },
      {
        text: "Name",
        align: "start",
        value: "releaseName",
      },
      {
        text: "Version",
        align: "start",
        value: "versions",
      },
      {
        text: "Maturity",
        align: "center",
        value: "experimental",
        filterable: true,
      },
      {
        text: "Hardware requirement", 
        value: "resourceRequirement",
        align: "start",
      },
      { text: "Action", 
        value: "installed",
        align: "start"
      },
      {
        text: "Ready",
        align: "center",
        value: "successful",
      },
      {
        text: "Application links",
        align: "start",
        value: "links",
      },
    ],
  }),
  created() {},
  mounted() {
    this.getHelmCharts();
    this.startExtensionsInterval();
  },
  computed: {
    filteredLaunchedAppLinks(): any {
      if (this.launchedAppLinks !== null) {
        return this.launchedAppLinks.filter((i: any) => {
          let devFilter = false;
          let kindFilter = false;
          let resourceFilter = false;

          if (this.selectedFilters.includes("Experimental") && i.experimental === "yes") {
            devFilter = true;
          } else if (this.selectedFilters.includes("Stable") && i.experimental === "no") {
            devFilter = true;
          }

          if (this.selectedFilters.includes("Applications") && i.kind === "application") {
            kindFilter = true;
          } else if (this.selectedFilters.includes("Workflows") && i.kind === "dag") {
            kindFilter = true;
          }

          if (this.selectedFilters.includes("CPU") && i.resourceRequirement == "cpu") {
            resourceFilter = true;
          } else if (
            this.selectedFilters.includes("GPU") &&
            i.resourceRequirement == "gpu"
          ) {
            resourceFilter = true;
          }

          return devFilter && kindFilter && resourceFilter;
        });
      } else {
        this.loading = true;
        return [];
      }
    },
    fileExtension(): any {
      return this.file ? this.file.name.split(".").pop() : "";
    },
    labelIdle(): any {
      // return "Drop files - allowed types: " + this.allowedFileTypes.join(", ")
      return "Upload chart (.tgz) or container (.tar) files";
    },

    ...mapGetters([
      "currentUser",
      "isAuthenticated",
      "commonData",
      "launchApplicationData",
      "availableApplications",
    ]),
  },
  methods: {
    handleFileUpload(file: File, key: string) {
      console.log("file", file)
      if (file && file.type === "application/json") {
        const reader = new FileReader();

        reader.onload = (e: ProgressEvent<FileReader>) => {
          try {
            const contents = e.target?.result as string;
            // Parse the contents as JSON and update popUpExtension[key]
            // TODO transfer as .json into kube-helm-api (needs to be adjusted)
            this.popUpExtension[key] = JSON.stringify(JSON.parse(contents));
            console.log("Read extension param file", this.popUpExtension);
          } catch (error) {
            console.error("Error parsing JSON file:", error);
          }
        };

        reader.onerror = (error) => {
          console.error("Error reading file:", error);
        };

        reader.readAsText(file);
      } else {
        console.error("Invalid file type. Please upload a JSON file.");
      }
    },
    getHref(link: string) {
      return link.match(/^:(\d+)(.*)/)
        ? "http://" + window.location.hostname + link
        : link;
    },
    fileStart(file: any) {
      console.log("filestart", file);
    },
    fileComplete(error: any, file: any) {
      if (error !== null) {
        console.log("filepond file upload error", error);
        return;
      } else {
        console.log("successfully uploaded file", file);
        let fname = file.filename;
        let fExt = file.fileExtension;
        if (fExt == "tar") {
          console.log("importing container...");
          kaapanaApiService
            .helmApiGet("/import-container", { filename: fname }, 120000)
            .then((response: any) => {
              console.log(response.data);
            })
            .catch((err: any) => {
              console.log(
                "Failed to import container " + fname,
                "error: ",
                err.response.data
              );
            });
        }
      }
    },
    checkDeploymentReady(item: any) {
      if (
        item["multiinstallable"] == "yes" &&
        item["chart_name"] == item["releaseName"]
      ) {
        return false;
      }
      if (item["available_versions"][item.version]["deployments"].length > 0) {
        return item["available_versions"][item.version]["deployments"][0].ready;
      }
      return false;
    },
    getKubeStatus(item: any) {
      if (
        item["multiinstallable"] == "yes" &&
        item["chart_name"] == item["releaseName"]
      ) {
        return "";
      }
      if (item["available_versions"][item.version]["deployments"].length > 0) {
        let statArr: any =
          item["available_versions"][item.version]["deployments"][0]["kube_status"];
        if (typeof statArr != "string" && statArr.length > 3) {
          let count: any = {};
          let s = "";
          for (let i = 0; i < statArr.length; i++) {
            let key = "";
            if (typeof statArr[i] == "string") {
              let stat = statArr[i];
              key = stat.charAt(0).toUpperCase() + stat.slice(1);
            } else {
              let stat = statArr[i];
              key += stat.charAt(0).toUpperCase() + stat.slice(1);
            }

            if (key in count) {
              count[key] += 1;
            } else {
              count[key] = 1;
            }
          }
          for (let k in count) {
            s += k + ": " + String(count[k]) + " ,\n";
          }
          return s.slice(0, s.length - 2);
        } else if (typeof statArr != "string" && statArr.length > 0) {
          let s = "";
          for (let i = 0; i < statArr.length; i++) {
            let stat = statArr[i];
            let key = stat.charAt(0).toUpperCase() + stat.slice(1);
            s += key + ", ";
          }
          return s.slice(0, s.length - 2);
        } else if (typeof statArr == "string" && statArr.length > 0) {
          let s = statArr;
          return s.charAt(0).toUpperCase() + s.slice(1);
        } else {
          return "";
        }
      }
      return "";
    },
    getHelmStatus(item: any) {
      if (
        item["multiinstallable"] == "yes" &&
        item["chart_name"] == item["releaseName"]
      ) {
        return "";
      }
      if (item["available_versions"][item.version]["deployments"].length > 0) {
        let s = item["available_versions"][item.version]["deployments"][0]["helm_status"];
        return s.charAt(0).toUpperCase() + s.slice(1);
      }
      return "";
    },
    checkInstalled(item: any) {
      if (
        item["multiinstallable"] == "yes" &&
        item["chart_name"] == item["releaseName"]
      ) {
        return "no";
      }
      if (item["available_versions"][item.version]["deployments"].length > 0) {
        return "yes";
      }
      return "no";
    },
    getHelmCharts() {
      let params = {
        repo: "kaapana-public",
      };
      kaapanaApiService
        .helmApiGet("/extensions", params)
        .then((response: any) => {
          this.launchedAppLinks = response.data;
          this.launchedAppLinks = this.launchedAppLinks.map((item: any) => ({
            documentation: item.annotations?.documentation ?? null,
            ...item,
          }));
          // console.log(JSON.stringify(this.launchedAppLinks));
          if (this.launchedAppLinks !== null) {
            this.loading = false;
          }
        })
        .catch((err: any) => {
          this.loading = false;
          console.log(err);
        });
    },
    startExtensionsInterval() {
      this.polling = window.setInterval(() => {
        this.getHelmCharts();
      }, 5000);
    },
    clearExtensionsInterval() {
      window.clearInterval(this.polling);
    },
    updateExtensions() {
      this.loading = true;
      this.clearExtensionsInterval();
      this.startExtensionsInterval();
      kaapanaApiService
        .helmApiGet("/update-extensions", {})
        .then((response: any) => {
          this.loading = false;
          console.log(response.data);
        })
        .catch((err: any) => {
          this.loading = false;
          console.log(err);
        });
    },
    deleteChart(item: any, helmCommandAddons: any = "") {
      let params = {
        release_name: item.releaseName,
        release_version: item.version,
        helm_command_addons: helmCommandAddons,
      };
      console.log("params", params);
      this.loading = true;
      this.clearExtensionsInterval();
      this.startExtensionsInterval();
      kaapanaApiService
        .helmApiPost("/helm-delete-chart", params)
        .then((response: any) => {
          console.log("helm delete response", response);
          item.installed = "no";
          item.successful = "pending";
        })
        .catch((err: any) => {
          console.log("helm delete error", err);
          this.loading = false;
        });
    },

    resetFormInfo(key: any) {
      this.popUpDialog[key] = false;
      if (this.$refs.popUpForm !== undefined) {
        this.popUpExtension = {} as any;
        (this.$refs.popUpForm as Vue & { reset: () => any }).reset();
      }
    },

    getFormInfo(item: any) {
      this.popUpDialog[item.releaseName] = false;
      this.popUpItem = {} as any;

      if (item["extension_params"] && Object.keys(item["extension_params"]).length > 0) {
        this.popUpDialog[item.releaseName] = true;
        this.popUpItem = item;
        for (let key of Object.keys(item["extension_params"])) {
          this.popUpExtension[key] = item["extension_params"][key]["default"];
        }
      } else {
        this.installChart(item);
      }
    },

    submitForm(key: any) {
      // this is the same as `this.$refs.popUpForm.validate()` but it raises a build error
      if ((this.$refs.popUpForm as Vue & { validate: () => boolean }).validate()) {
        this.popUpDialog[key] = false;
        this.installChart(this.popUpItem);
      }
    },

    addExtensionParams(payload: any) {
      let params = JSON.parse(JSON.stringify(this.popUpExtension));
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
          // string or single selectable list item
          s = v;
        }

        res[key] = s;
      }
      payload["extension_params"] = res;
      return payload;
    },

    installChart(item: any) {
      let payload = {
        name: item.name,
        version: item.version,
        keywords: item.keywords,
      } as any;

      console.log("payload", payload);
      if (Object.keys(this.popUpExtension).length > 0) {
        payload = this.addExtensionParams(payload);
      }

      this.loading = true;
      this.clearExtensionsInterval();
      this.startExtensionsInterval();
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
          this.loading = false;
        });
    },
  },
  beforeDestroy() {
    this.clearExtensionsInterval();
  },
});
</script>

<style lang="scss">
a {
  text-decoration: none;
}

.dragdrop {
  margin: auto;
  width: 95%;
  height: 8vh;
  position: relative;
  margin-bottom: 2vh;
  border: 2px dashed #eee;
}

.dragdrop:hover {
  border: 2px solid #2e94c4;
}

.dragdrop:hover .dragdrop-title {
  color: #1975a0;
}

.dragdrop-info {
  color: #a8a8a8;
  position: absolute;
  top: 50%;
  width: 100%;
  transform: translate(0, -50%);
  text-align: center;
}

.dragdrop-title {
  color: #787878;
}

.dragdrop input {
  position: absolute;
  cursor: pointer;
  top: 0px;
  right: 0;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
}

.dragdrop-upload-limit-info {
  display: flex;
  justify-content: flex-start;
  flex-direction: column;
}

.dragdrop-over {
  background: #5c5c5c;
  opacity: 0.8;
}

.dragdrop-uploaded {
  margin: auto;
  width: 95%;
  height: 8vh;
  position: relative;
  margin-bottom: 2vh;
  border: 2px dashed #eee;
}

.dragdrop-uploaded-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #a8a8a8;
  position: absolute;
  top: 50%;
  width: 100%;
  transform: translate(0, -50%);
  text-align: center;
}

.upload {
  margin-top: 10px;
  padding-top: 100px;
  padding-bottom: 10px;
}

.cell-content {
  display: flex;
  align-items: center; /* Align text and icon */
  justify-content: space-between; /* Ensures text stays left, icon stays right */
  width: 100%;
  height: 100%;
}

.text-content {
  display: flex;
  flex-direction: column;
}

.first-line {
  font-size: 16px;
  font-weight: bold;
}

.second-line {
  font-size: 12px;
  color: gray;
}

.cell-icon {
  font-size: 1.5em; /* Adjust as needed */
  align-self: stretch; /* Ensures icon takes max cell height */
}
</style>
