<template lang="pug">
  .workflow-applications
    v-container(grid-list-lg, text-left)
      v-card
        v-card-title
          v-row
            v-col(cols="12", sm="5")
              span Platforms &nbsp;
                v-tooltip(bottom="")
                  template(v-slot:activator="{ on, attrs }")
                    v-icon(
                      @click="showDialog = true",
                      color="primary",
                      dark="",
                      v-bind="attrs",
                      v-on="on"
                    )
                      | mdi-cloud-refresh-outline
                  span Click to download platforms from different registries, this might take some time.
              br
            v-col(cols="12", sm="2")
              v-select(
                label="Kind",
                :items="['All', 'Platforms']",
                v-model="extensionKind",
                hide-details=""
              )
            v-col(cols="12", sm="2")
              v-select(
                label="Version",
                :items="['All', 'Stable', 'Experimental']",
                v-model="extensionExperimental",
                hide-details=""
              )
            v-col(cols="12", sm="3")
              v-text-field(
                v-model="search",
                append-icon="mdi-magnify",
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
          loading-text="Waiting a few seconds..."
        )
          template(v-slot:item.releaseName="{ item }")
            span {{ item.releaseName }} &nbsp;
              a(
                :href="link",
                target="_blank",
                v-for="link in item.links",
                v-if="item.links.length < 3"
                :key="item.link"
              )
                v-icon(color="primary") mdi-open-in-new
          template(v-slot:item.versions="{ item }") 
            v-select(
              :items="item.versions",
              v-model="item.version",
              hide-details=""
            )
            //- span(v-if="item.installed === 'yes'") {{ item.version }}
          template(v-slot:item.successful="{ item }")
            v-progress-circular(
              v-if="item.successful === 'pending'",
              indeterminate,
              color="primary"
            )
            v-icon(v-if="checkDeploymentReady(item) === true && item.successful !== 'pending'", color="green") mdi-check-circle
            v-icon(v-if="item.successful === 'no'", color="red") mdi-alert-circle
          template(v-slot:item.kind="{ item }")
            v-tooltip(bottom="", v-if="item.kind === 'dag'")
              template(v-slot:activator="{ on, attrs }")
                v-icon(color="primary", dark="", v-bind="attrs", v-on="on")
                  | mdi-gamepad-variant
              span A workflow or algorithm that will be added to Airflow DAGs
            v-tooltip(bottom="", v-if="item.kind === 'application'")
              template(v-slot:activator="{ on, attrs }")
                v-icon(color="primary", dark="", v-bind="attrs", v-on="on")
                  | mdi-application-outline
              span An application to work with
            v-tooltip(bottom="", v-if="item.kind === 'platform'")
              template(v-slot:activator="{ on, attrs }")
                v-icon(color="primary", dark="", v-bind="attrs", v-on="on")
                  | mdi-monitor-dashboard
              span A standalone platform that contains different services
          template(v-slot:item.helmStatus="{ item }")
            span {{ getHelmStatus(item) }}
          template(v-slot:item.kubeStatus="{ item }")
            span {{ getKubeStatus(item) }}
          template(v-slot:item.experimental="{ item }")
            v-tooltip(bottom="", v-if="item.experimental === 'yes'")
              template(v-slot:activator="{ on, attrs }")
                v-icon(color="primary", dark="", v-bind="attrs", v-on="on")
                  | mdi-test-tube
              span Experimental extension or DAG, not tested yet!
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
                v-if="item.extension_params !== undefined || item.extension_params!== 'null'"
                v-model="popUpDialog[item.releaseName]"
                :retain-focus="false"
                max-width="600px"
                persistent
                scrollable
              )
                v-card
                  v-card-title Set up Platform {{ popUpItem.name }}
                  v-card-text
                    v-form.px-3(ref="popUpForm")
                      template(v-for="(param, key) in popUpItem.extension_params")
                        span(v-if="param.type == 'group_name'" style="font-weight:bold;font-size:25px;align:left") {{ param.default }}
                        v-text-field(
                          v-if="param.type == 'string'"
                          :label="key"
                          v-model="popUpExtension[key]"
                          clearable,
                          :rules="param.required ? popUpRulesStr : []"                        
                        )
                        v-checkbox(
                          v-if="param.type == 'bool' || param.type == 'boolean'"
                          :label="key"
                          v-model="popUpExtension[key]"
                        )
                        v-select(
                          v-if="param.type == 'list_single'"
                          :items="param.value"
                          :label="key"
                          v-model="popUpExtension[key]"
                          :rules="param.required ? popUpRulesSingleList : []"
                          clearable
                        )
                        v-select(
                          v-if="param.type == 'list_multi'"
                          multiple
                          :items="param.value"
                          :item-text="param.default"
                          :label="key"
                          v-model="popUpExtension[key]"
                          :rules="param.required ? popUpRulesMultiList : []"
                          clearable
                        )
                  v-card-actions
                    v-spacer
                    v-btn(color="primary", @click="resetFormInfo(item.releaseName)") Close
                    v-btn(color="primary", @click="submitForm(item.releaseName)") Submit
  
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
                v-card-text If an installation gets stuck in the "Pending" state, it is likely due to an error in the Helm chart. You can force to uninstall the extension to resolve the issue.
                v-card-actions
                  v-btn(
                    @click="deleteChart(item, helmCommandAddons='--no-hooks');",
                    color="primary",
                    min-width="160px",
                  ) 
                    span(v-if="item.multiinstallable === 'yes'") Force Delete
                    span(v-if="item.multiinstallable === 'no'") Force Uninstall

      //- Dialog for registry configuration - moved outside the data table
      v-dialog(v-model="showDialog", max-width="600px")
        v-card
          v-card-title
            span.text-h5 Registry Configuration
          v-card-text
            v-container
              v-form(ref="form", v-model="valid")
                v-row
                  v-col(cols="12")
                    v-text-field(
                      v-model="formData.container_registry_url",
                      label="Container Registry URL",
                      required,
                      outlined,
                      :rules="[v => !!v || 'Registry URL is required']"
                    )
                  v-col(cols="12")
                    v-text-field(
                      v-model="formData.container_registry_username",
                      label="Registry Username",
                      outlined
                    )
                  v-col(cols="12")
                    v-text-field(
                      v-model="formData.container_registry_password",
                      label="Registry Password",
                      type="password",
                      outlined
                    )
                  v-col(cols="12")
                    v-text-field(
                      v-model="formData.platform_name",
                      label="Platform Name",
                      outlined,
                      hint="Default: kaapana-admin-chart"
                    )
                  v-col(cols="12")
                    v-text-field(
                      v-model="formData.auth_url",
                      label="Auth URL",
                      outlined,
                      hint="registry auth URL example: https://codebase.helmholtz.cloud/jwt/auth"
                    )
          v-card-actions
            v-spacer
            v-btn(color="blue darken-1", text, @click="showDialog = false") Cancel
            v-btn(
              color="blue darken-1",
              text,
              @click="submitFormRegistry",
              :loading="loading",
              :disabled="!valid"
            ) Submit
      //- Snackbar for showing response messages - moved outside the data table
      v-snackbar(v-model="snackbar", :color="snackbarColor", timeout="5000")
        | {{ snackbarText }}
        template(v-slot:action="{ attrs }")
          v-btn(text, v-bind="attrs", @click="snackbar = false") Close
    </template>
  <script lang="ts">

  import Vue from "vue";
  import { mapGetters } from "vuex";
  import kaapanaApiService from "@/common/kaapanaApi.service";
  
  export default Vue.extend({
    data: () => ({
      polling: 0,
      launchedAppLinks: [] as any,
      search: "",
      extensionExperimental: "Stable",
      extensionKind: "All",
      popUpDialog: {} as any,
      popUpItem: {} as any,
      popUpChartName: "",
      popUpExtension: {} as any,
      showOptionalFields: false,
      loading: true,
      popUpRulesStr: [
        (v: any) => v && v.length > 0 || 'Empty string field'
      ],
      popUpRulesSingleList: [
        (v: any) => v && v.length > 0 || "Empty single-selectable list field"
      ],
      popUpRulesMultiList: [
        (v: any) => v.length > 0 || "Empty multi-selectable list field"
      ],
      showDialog: false,
      valid: false,
      formData: {
        container_registry_url: "",
        container_registry_username: "",
        container_registry_password: "",
        platform_name: "kaapana-admin-chart",
        auth_url: ""
      },
      snackbar: false,
      snackbarText: "",
      snackbarColor: "success",
      headers: [
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
          text: "Kind",
          align: "start",
          value: "kind",
        },
        {
          text: "Description",
          align: "start",
          value: "description",
        },
        {
          text: "Helm Status",
          align: "start",
          value: "helmStatus",
        },
        {
          text: "Kube Status",
          align: "start",
          value: "kubeStatus",
        },
        {
          text: "Experimental",
          align: "start",
          value: "experimental",
        },
        {
          text: "Ready",
          align: "start",
          value: "successful",
        },
        { text: "Action", value: "installed" },
      ],
    }),
    created() { },
    mounted() {
      this.getHelmCharts();
      this.startExtensionsInterval();
    },
    computed: {
      filteredLaunchedAppLinks(): any {
        if (this.launchedAppLinks !== null) {
          return this.launchedAppLinks.filter((i: any) => {
            let devFilter = true;
            let kindFilter = true;
  
            if (this.extensionExperimental == "Stable" && i.experimental === "yes") {
              devFilter = false;
            } else if (this.extensionExperimental == "Experimental" && i.experimental === "no") {
              devFilter = false;
            }
  
            if (this.extensionKind == "Workflows" && (i.kind === "application" || i.kind === "platform")) {
              kindFilter = false;
            } else if (this.extensionKind == "Applications" && (i.kind === "dag"  || i.kind === "platform")) {
              kindFilter = false;
            } else if (this.extensionKind == "Platforms" && (i.kind === "dag"  || i.kind === "application")) {
              kindFilter = false;
            }
            return devFilter && kindFilter;
          });
        } else {
          this.loading = true;
          return [];
        }
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
      checkDeploymentReady(item: any) {
        if (item["multiinstallable"] == "yes" && item["chart_name"] == item["releaseName"]) {
          return false
        }
        if (item["available_versions"][item.version]["deployments"].length > 0) {
          return item["available_versions"][item.version]["deployments"][0].ready
        }
        return false
      },
      getKubeStatus(item: any) {
        if (item["multiinstallable"] == "yes" && item["chart_name"] == item["releaseName"]) {
          return ""
        }
        if (item["available_versions"][item.version]["deployments"].length > 0) {
          let statArr: any = item["available_versions"][item.version]["deployments"][0]["kube_status"]
          if (typeof (statArr) != "string" && statArr.length > 3) {
            let count: any = {}
            let s = ""
            for (let i = 0; i < statArr.length; i++) {
              let key = ""
              if (typeof (statArr[i]) == "string") {
                let stat = statArr[i]
                key = stat.charAt(0).toUpperCase() + stat.slice(1);
              } else {
                let stat = statArr[i]
                key += stat.charAt(0).toUpperCase() + stat.slice(1);
              }
  
              if (key in count) {
                count[key] += 1;
              } else {
                count[key] = 1;
              }
            }
            for (let k in count) {
              s += k + ": " + String(count[k]) + " ,\n"
            }
            return s.slice(0, s.length - 2)
          } else if (typeof (statArr) != "string" && statArr.length > 0) {
            let s = ""
            for (let i = 0; i < statArr.length; i++) {
              let stat = statArr[i]
              let key = stat.charAt(0).toUpperCase() + stat.slice(1);
              s += key + ", "
            }
            return s.slice(0, s.length - 2);
          } else if (typeof (statArr) == "string" && statArr.length > 0) {
            let s = statArr
            return s.charAt(0).toUpperCase() + s.slice(1);
          } else {
            return ""
          }
  
  
        }
        return ""
      },
      getHelmStatus(item: any) {
        if (item["multiinstallable"] == "yes" && item["chart_name"] == item["releaseName"]) {
          return ""
        }
        if (item["available_versions"][item.version]["deployments"].length > 0) {
          let s = item["available_versions"][item.version]["deployments"][0]["helm_status"]
          return s.charAt(0).toUpperCase() + s.slice(1);
        }
        return ""
      },
      checkInstalled(item: any) {
        if (item["multiinstallable"] == "yes" && item["chart_name"] == item["releaseName"]) {
          return "no"
        }
        if (item["available_versions"][item.version]["deployments"].length > 0) {
          return "yes"
        }
        return "no"
      },
      getHelmCharts() {
        let params = {
          repo: "kaapana-public",
        };
        kaapanaApiService
          .helmApiGet("/platforms", params)
          .then((response: any) => {
            this.launchedAppLinks = response.data;
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
      deleteChart(item: any, helmCommandAddons: any = '') {
        let params = {
          release_name: item.releaseName,
          release_version: item.version,
          helm_command_addons: helmCommandAddons,
          helm_namespace: item.available_versions[item.version].deployments[0].helm_info.namespace,
          platforms: true
        };
        console.log("params", params)
        this.loading = true;
        this.clearExtensionsInterval();
        this.startExtensionsInterval();
        kaapanaApiService
          .helmApiPost("/helm-delete-chart", params)
          .then((response: any) => {
            console.log("helm delete response", response)
            item.installed = "no";
            item.successful = "pending";
          })
          .catch((err: any) => {
            console.log("helm delete error", err)
            this.loading = false;
          });
      },
  
      resetFormInfo(key: any) {
        this.popUpDialog[key] = false
        if (this.$refs.popUpForm !== undefined) {
          this.popUpExtension = {} as any;
          (this.$refs.popUpForm as Vue & { reset: () => any }).reset()
        }
      },
  
      getFormInfo(item: any) {
        this.popUpDialog[item.releaseName] = false;
        this.popUpItem = {} as any;
  
        if (item["extension_params"] && Object.keys(item["extension_params"]).length > 0) {
          this.popUpDialog[item.releaseName] = true;
          this.popUpItem = item;

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
        let params = JSON.parse(JSON.stringify(this.popUpExtension))
        console.log("add parameters", params)
  
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
          } else { // string or single selectable list item
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
          platforms: "true",
          blocking: "true",
        } as any;
  
        console.log("payload", payload)
        if (Object.keys(this.popUpExtension).length > 0) {
          payload = this.addExtensionParams(payload);
        }
  
        this.loading = true;
        this.clearExtensionsInterval();
        this.startExtensionsInterval();
        kaapanaApiService
          .helmApiPost("/helm-install-chart", payload)
          .then((response: any) => {
            console.log("helm install response", response)
            item.installed = "yes";
            if (item.multiinstallable === 'yes') {
              item.successful = "justLaunched";
            } else {
              item.successful = "pending";
            }
          })
          .catch((err: any) => {
            console.log("helm install error", err)
            this.loading = false;
          });
      },
      submitFormRegistry() {
        //if (!this.$refs.form.validate()) return;
        
        this.loading = true;
        
          // Construct query parameters
          const params = new URLSearchParams();
          for (const [key, value] of Object.entries(this.formData)) {
            if (value) params.append(key, value);
          }
          kaapanaApiService
            .helmApiGet("/available-platforms", params)
            .then((response: any) => {
              this.showSnackbar("Platforms retrieved successfully", "success");
              this.showDialog = false;
              console.log(response.data);
              // Emit event to parent component with the data
              this.showSnackbar(response.data, "success");
            })
            .catch((err: any) => {
              this.loading = false;
              this.showSnackbar(`Network error: ${err.message}`, "error");
              console.log(err);
            })
            .finally(() => {
              this.loading = false;
            });
      },
      showSnackbar(text: any, color = "success") {
        this.snackbarText = text;
        this.snackbarColor = color;
        this.snackbar = true;
      },
      getPlatforms() {
        this.showDialog = true;
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
  </style>
