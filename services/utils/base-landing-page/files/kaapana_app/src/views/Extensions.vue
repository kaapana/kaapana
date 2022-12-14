<template lang="pug">
.workflow-applications
  v-container(grid-list-lg, text-left)
    v-card
      v-card-title
        v-row
          v-col(cols="12", sm="5")
            span Applications and workflows &nbsp;
              v-tooltip(bottom="")
                template(v-slot:activator="{ on, attrs }")
                  v-icon(
                    @click="updateExtensions()",
                    color="primary",
                    dark="",
                    v-bind="attrs",
                    v-on="on"
                  )
                    | mdi-cloud-download-outline
                span By clicking on this icon it will try to download the latest extensions.
            br
            span(style="font-size: 14px") On 
              a(href="https://kaapana.readthedocs.io/", target="_blank") readthedocs
              |
              | you find a description of each extension
          v-col(cols="12", sm="2")
            v-select(
              label="Kind",
              :items="['All', 'Workflows', 'Applications']",
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
      div(v-if='uploadPerc != 100 && file && loadingFile')
        div(:class="['dragdrop']")
          .dragdrop-info()
            span.fa.fa-cloud-upload.dragdrop-title
            v-tooltip(bottom="")
              template(v-slot:activator="{on}")
                v-icon(
                  @click="cancelUploadFile()",
                  color="primary",
                  dark="",
                  v-on="on"
                    )
                      | mdi-close-circle
              span Cancel the upload
            span.dragdrop-title    Uploading file... {{uploadPerc}} % 
            .dragdrop-upload-limit-info
              div filename: {{file.name}} | file size: {{(file.size / 1000000).toFixed(2)}} MB
      div(v-else-if='uploadPerc == 100 && !file && !loadingFile')
        div(:class="['dragdrop', dragging ? 'dragdrop-over' : '']" @dragenter='dragging = true' @dragleave='dragging = false')
          .dragdrop-uploaded-info(@drag='onChange')
            span.dragdrop-title {{fileResponse}}
            .dragdrop-upload-limit-info
              div Upload completed. Select another chart(.tgz) or container(.tar) file
          input(type='file' @change='onChange')
      div(v-else-if='file && !loadingFile')
        div(:class="['dragdrop', dragging ? 'dragdrop-over' : '']" @dragenter='dragging = true' @dragleave='dragging = false')
          .dragdrop-info(@drag='onChange')
            span.fa.fa-cloud-upload.dragdrop-title
            span.dragdrop-title {{fileResponse}}
            .dragdrop-upload-limit-info
              div Please try again
          input(type='file' @change='onChange')
      div(v-else='')
        div(:class="['dragdrop', dragging ? 'dragdrop-over' : '']" @dragenter='dragging = true' @dragleave='dragging = false')
          .dragdrop-info(@drag='onChange')
            span.fa.fa-cloud-upload.dragdrop-title
            span.dragdrop-title Drag/select chart(.tgz) or container(.tar) file for upload
            .dragdrop-upload-limit-info
              div file types: tgz,tar  |  max size: 20 GB
          input(type='file' @change='onChange')


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
              :key="item.link"
            )
              v-icon(color="primary") mdi-open-in-new
        template(v-slot:item.versions="{ item }") 
          v-select(
            v-if="item.installed === 'no'",
            :items="item.versions",
            v-model="item.version",
            hide-details=""
          )
          span(v-if="item.installed === 'yes'") {{ item.version }}
        template(v-slot:item.successful="{ item }")
          v-progress-circular(
            v-if="item.successful === 'pending'",
            indeterminate,
            color="primary"
          )
          v-icon(v-if="item.successful === 'yes'", color="green") mdi-check-circle
          v-icon(v-if="item.successful === 'no'", color="red") mdi-alert-circle
        template(v-slot:item.kind="{ item }")
          v-tooltip(bottom="", v-if="item.kind === 'dag'")
            template(v-slot:activator="{ on, attrs }")
              v-icon(color="primary", dark="", v-bind="attrs", v-on="on")
                | mdi-chart-timeline-variant
            span A workflow or algorithm that will be added to Airflow DAGs
          v-tooltip(bottom="", v-if="item.kind === 'application'")
            template(v-slot:activator="{ on, attrs }")
              v-icon(color="primary", dark="", v-bind="attrs", v-on="on")
                | mdi-laptop
            span An application to work with
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
            v-if="item.installed === 'yes' && item.successful !== 'pending' && item.successful !== 'justLaunched'"
          ) 
            span(v-if="item.multiinstallable === 'yes'") Delete
            span(v-if="item.multiinstallable === 'no'") Uninstall
          v-btn(
            @click="getFormInfo(item)",
            color="primary",
            min-width = "160px",
            v-if="item.installed === 'no' && item.successful !== 'pending'"
          ) 
            span(v-if="item.multiinstallable === 'yes'") Launch
            span(v-if="item.multiinstallable === 'no'") Install

            v-dialog(
              v-if="item.extension_params !== undefined || item.extension_params!== 'null'"
              v-model="popUpDialog"
              :retain-focus="false"
              max-width="600px"
              @click:outside="resetFormInfo()"
            )
              v-card
                v-card-title Setup Extension {{ popUpItem.name }}
                v-card-text
                  v-form.px-3(ref="popUpForm")
                    template(v-for="(param, key) in popUpItem.extension_params")
                      v-text-field(
                        v-if="param.type == 'string'"
                        :label="key + ':' + param.definition + ' [default: ' + param.default + ']' "
                        v-model="popUpExtension[key]"
                        clearable,
                        :rules="popUpRulesStr"
                      )
                      v-select(
                        v-if="param.type == 'list_single'"
                        :items="param.value"
                        :label="key + ':' + param.definition + ' [default: ' + param.default + ']' "
                        v-model="popUpExtension[key]"
                        :rules="popUpRulesSingleList"
                        clearable
                      )
                      v-select(
                        v-if="param.type == 'list_multi'"
                        multiple
                        :items="param.value"
                        :item-text="param.default"
                        :label="key + ':' + param.definition + ' [default: ' + param.default + ']' "
                        v-model="popUpExtension[key]"
                        :rules="popUpRulesMultiList"
                        clearable
                      )

                  v-btn(color="primary", @click="submitForm()") Submit

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
import request from "@/request";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";
import { CHECK_AUTH } from '@/store/actions.type';

export default Vue.extend({
  data: () => ({
    file: '' as any,
    fileResponse: '',
    dragging: false,
    loadingFile: false,
    conn: null as WebSocket | null,
    uploadChunksMethod: 'http' as string, // set 'ws' for websocket otherwise 'http'
    cancelUpload: false,
    uploadPerc: 0,
    loading: true,
    polling: 0,
    launchedAppLinks: [] as any,
    search: "",
    extensionExperimental: "Stable",
    extensionKind: "All",
    popUpDialog: false,
    popUpItem: {} as any,
    popUpChartName: "",
    popUpExtension: {} as any,
    popUpRulesStr: [
      (v: any) => v && v.length > 0 || 'Empty string field'
    ],
    popUpRulesSingleList: [
      (v: any) => v && v.length > 0 || "Empty single-selectable list field"
    ],
    popUpRulesMultiList: [
      (v: any) => v.length > 0 || "Empty multi-selectable list field"
    ],
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
    this.startExtensionsInterval()
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

          if (this.extensionKind == "Workflows" && i.kind === "application") {
            kindFilter = false;
          } else if (this.extensionKind == "Applications" && i.kind === "dag") {
            kindFilter = false;
          }
          return devFilter && kindFilter;
        });
      } else {
        this.loading = true;
        return [];
      }
    },
    fileExtension(): any {
      return (this.file) ? this.file.name.split('.').pop() : '';
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
    onChange(e: any) {
      var files = e.target.files || e.dataTransfer.files;

      if (!files.length) {
        this.dragging = false;
        return;
      }

      this.uploadFile(files[0]);
    },
    cancelUploadFile() {
      console.log("cancel upload called")
      if (this.conn) this.conn.close()
      this.cancelUpload = true
    },
    uploadChunksWS() {
      // websocket version
      let chunkSize = 10 * 1024 * 1024
      let iters = Math.ceil(this.file.size / chunkSize)
      let clientID = Date.now();
      // console.log("clientID", clientID)
      let baseURL: any = request.defaults.baseURL
      if (baseURL.includes("//")) {
        let sp = baseURL.split("//")
        baseURL = sp[1]
      }
      let conn = new WebSocket("ws://" + baseURL + "/file_chunks/" + String(clientID));
      conn.onclose = (closeEvent) => {
        console.log("connection closed", closeEvent)
        this.conn = null;
        this.loadingFile = false
        this.fileResponse = "Upload Failed: connection closed"
        let fname = this.file.name
        this.file = ''
        if (this.uploadPerc == 100) {
          this.fileResponse = "Importing container " + fname
          console.log("importing container...")
          kaapanaApiService
            .helmApiGet("/import-container", { filename: fname })
            .then((response: any) => {
              this.fileResponse = "Successfully imported container " + fname
            })
            .catch((err: any) => {
              console.log(err);
              this.fileResponse = "Failed to import container " + fname
            });
        }
      }
      conn.onerror = (errorEvent) => {
        this.conn = null;
        console.log("connection error", errorEvent)
        conn.close()
      }
      conn.onopen = (openEvent) => {
        this.conn = conn;
        console.log("Successfully connected", openEvent)
      }

      let i = -1

      conn.onmessage = (msg) => {
        if (!this.conn) {
          console.log("connection not established, returning")
          return
        }
        // console.log("msg", msg)
        var jmsg
        try {
          jmsg = JSON.parse(msg.data)
        }
        catch (err) {
          console.log("JSON parse failed", err)
          if (this.conn) { this.conn.close() }
          this.loadingFile = false
          return
        }

        if (jmsg["success"] == true && jmsg["index"] == i) {
          // console.log("previous send for index", i, "was successful, proceeding...")
          if (i != -1) { this.uploadPerc = Math.floor((i / iters) * 100) }
          i++;

          if (i > iters) {
            this.uploadPerc = 100;
            console.log("upload completed, closing connection")
            if (this.conn) { this.conn.close() }
            return
          }

          const chunk = this.file.slice(i * chunkSize, (i + 1) * chunkSize);
          if (this.conn) {
            // console.log("sending ws msg chunk index", i)
            this.conn.send(chunk)
          } else {
            // console.log("websocket connection lost");
            this.loadingFile = false;
          }
        }
        else {
          // console.log("success", jmsg["success"], "expected index", i, "got", jmsg["index"])
          console.log("something went wrong, closing the connection")
          if (this.conn) {
            this.conn.close()
            this.loadingFile = false
          }
        }
      }

      // send file info first
      setTimeout(() => {
        if (this.conn) {
          // console.log("sending ws msg", { name: file.name, fileSize: file.size, chunkSize: chunkSize })
          this.conn.send(JSON.stringify({ name: this.file.name, fileSize: this.file.size, chunkSize: chunkSize }))
        }
      }, 1500);
    },
    uploadFile(file: any) {
      let uploadChunks = false;

      console.log("file.name", file.name)
      console.log("file.size", file.size)
      console.log("file.type", file.type)

      if (!file.type.match('application/x-compressed') && !file.type.match('application/x-tar')) {
        alert('please upload a tgz or tar file');
        this.dragging = false;
        return;
      }

      if (file.size > 20000000000) {
        alert('file size should not be over 20 GB.')
        this.dragging = false;
        return;
      } else if (file.size > 50000000) {
        console.log("file size greater than 50MB, using async upload")
        uploadChunks = true;
      }

      this.cancelUpload = false;
      this.file = file;
      this.dragging = false;
      this.loadingFile = true;
      this.uploadPerc = 0;

      if (!uploadChunks) {
        let formData = new FormData();

        formData.append("file", file);
        kaapanaApiService
          .helmApiPost(
            "/file",
            formData
          )
          .then((response: any) => {
            this.uploadPerc = 100
            console.log("upload file response", response)
            this.fileResponse = "Successfully uploaded " + this.file.name;
            this.file = ''
            this.loadingFile = false;
          }).catch((err: any) => {
            console.log("upload file error", err)
            this.fileResponse = "Upload Failed: " + err.data;
          });
      } else {
        this.uploadPerc = 0;

        if (this.uploadChunksMethod == "ws") {
          this.uploadChunksWS()
        } else {
          // http version
          let chunkSize = 5 * 1024 * 1024
          let iters = Math.ceil(this.file.size / chunkSize)

          // init
          let params = {
            name: this.file.name,
            fileSize: this.file.size,
            chunkSize: chunkSize,
            index: -1,
            endIndex: iters,
            chunk: "",
          }
          console.time("uploadFileChunks")
          this.uploadChunkHTTP(params, -1, iters)
        }

      }
    },
    uploadChunkHTTP(params: any, i: number, iters: number) {
      console.log("uploading chunk", i, "/", iters)
      kaapanaApiService
        .helmApiPost("/file_chunks", params)
        .then(async (resp: any) => {
          console.log("file chunks resp", resp)
          if (String(resp.data) != String(i) || resp.status != 200) {
            console.log("error in response", resp)
            this.loadingFile = false
            this.fileResponse = "Upload Failed"
            this.file = ''
            return
          }
          if (i >= iters) {
            console.log("upload completed")
            console.timeEnd("uploadFileChunks")
            //end
            this.uploadPerc = 100;
            this.loadingFile = false
            this.fileResponse = "Importing container " + this.file.name
            console.log("importing container...")
            kaapanaApiService
              .helmApiGet("/import-container", { filename: this.file.name })
              .then((response: any) => {
                this.fileResponse = "Successfully imported container " + this.file.name
              })
              .catch((err: any) => {
                console.log(err);
                this.fileResponse = "Failed to import container " + this.file.name
              });
            this.file = ''
            console.log("import completed")
            return
          } else {
            // loop
            if (this.cancelUpload) {
              console.log("cancelling upload")
              this.loadingFile = false
              this.file = ''
            }
            console.log(String(i) + "/" + String(iters), "was successful, proceeding...")
            if (i > 0) this.uploadPerc = Math.floor((i / iters) * 100)
            i++;
            if (i % 50 == 0) {
              this.$store
                .dispatch(CHECK_AUTH).then(() => {
                  console.log('still online')
                }).catch((err: any) => {
                  console.log('reloading')
                  location.reload()
                })
            }
            let chunkBlob = this.file.slice(i * params.chunkSize, (i + 1) * params.chunkSize);
            const chunk = await chunkBlob.text();
            params.chunk = chunk
            params.index = i
            this.uploadChunkHTTP(params, i, iters)
          }
        })
        .catch((err: any) => {
          // error
          console.log("error, index", i, ":", err)
          console.timeEnd("uploadFileChunks")
          this.loadingFile = false
          this.fileResponse = "Upload Failed: " + String(err)
          this.file = ''
          this.cancelUpload = true
          return
        });
    },
    getHelmCharts() {
      let params = {
        repo: "kaapana-public",
      };
      kaapanaApiService
        .helmApiGet("/extensions", params)
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
      // this.polling = window.setInterval(() => {
      //   this.getHelmCharts();
      // }, 5000);
    },
    clearExtensionsInterval() {
      // window.clearInterval(this.polling);
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
    deleteChart(item: any, helmCommandAddons: any = '') {
      let params = {
        release_name: item.releaseName,
        release_version: item.version,
        helm_command_addons: helmCommandAddons
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

    resetFormInfo() {
      if (this.$refs.popUpForm !== undefined) {
        this.popUpExtension = {} as any;
        (this.$refs.popUpForm as Vue & { reset: () => any }).reset()
      }
    },

    getFormInfo(item: any) {
      this.popUpDialog = false;
      this.popUpItem = {} as any;

      if (item["extension_params"] && Object.keys(item["extension_params"]).length > 0) {
        this.popUpDialog = true;
        this.popUpItem = item;
        for (let key of Object.keys(item["extension_params"])) {
          this.popUpExtension[key] = item["extension_params"][key]["default"]
        }
      } else {
        this.installChart(item);
      }
    },

    submitForm() {
      // this is the same as `this.$refs.popUpForm.validate()` but it raises a build error
      if ((this.$refs.popUpForm as Vue & { validate: () => boolean }).validate()) {
        this.popUpDialog = false
        this.installChart(this.popUpItem)
      }

    },

    addExtensionParams(payload: any) {
      let params = JSON.parse(JSON.stringify(this.popUpExtension))
      console.log("add parameters", params)

      let res = {} as any
      for (let key of Object.keys(params)) {
        let v = params[key]
        let s = "" as string
        // TODO: if more types like Object etc will exist as well, check them here
        if (Array.isArray(v) && v.length > 0) {
          for (let vv of v) {
            s += String(vv) + ","
          }
          s = s.slice(0, s.length - 1)
        } else { // string or single selectable list item
          s = v
        }

        res[key] = s
      }
      payload["extension_params"] = res
      return payload
    },

    installChart(item: any) {
      let payload = {
        name: item.name,
        version: item.version,
        keywords: item.keywords,
      };
      console.log("payload", payload)
      if (Object.keys(this.popUpExtension).length > 0) {
        payload = this.addExtensionParams(payload)
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
  },
  beforeDestroy() {
    this.clearExtensionsInterval()
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
  color: #1975A0;
}

.dragdrop-info {
  color: #A8A8A8;
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
  background: #5C5C5C;
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
  color: #A8A8A8;
  position: absolute;
  top: 50%;
  width: 100%;
  transform: translate(0, -50%);
  text-align: center;
}
</style>
