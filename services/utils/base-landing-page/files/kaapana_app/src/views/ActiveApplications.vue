<template lang="pug">
  .workflow-applications(style="max-width: 1000px; margin: 0 auto")
    IdleTracker
    v-container(grid-list-lg text-left fluid)
      v-expansion-panels(multiple v-model="openPanels")
        v-expansion-panel
          v-expansion-panel-header
            div
              .text-subtitle-1.font-weight-medium Applications requesting your input
              .text-caption.grey--text If a workflow has started an application, you will find a link to it here. Use the 'Finish Interaction' button to continue the workflow.
          v-expansion-panel-content
            .d-flex.align-center.justify-end.mb-2
              span.text-caption.mr-2 Sort by:
              v-btn-toggle(v-model="sortKey" mandatory dense)
                v-btn(value="name" small) Name
                v-btn(value="startedAt" small) Started
              v-btn.ml-2(icon small @click="sortDesc = !sortDesc")
                v-icon {{ sortDesc ? 'mdi-sort-descending' : 'mdi-sort-ascending' }}
            v-progress-linear(v-if="loadingTriggered" indeterminate)
            v-list(v-else two-line)
              template(v-if="sortedApps(triggeredApplications).length")
                v-list-item(v-for="item in sortedApps(triggeredApplications)" :key="item.releaseName")
                  v-list-item-icon.align-self-center
                    v-icon mdi-application
                  v-list-item-content
                    v-list-item-title.font-weight-bold {{ item.name }}
                    v-list-item-subtitle Started {{ item.createdAt }}
                  .d-flex.align-center.flex-wrap
                    v-tooltip(right)
                      template(v-slot:activator="{ on, attrs }")
                        span(v-bind="attrs" v-on="on")
                          v-btn(v-for="path in item.paths" :key="path" outlined :color="isFinishing(item) ? 'grey' : linkColor(item)" class="ma-1" @click="onLinkClick(item, path)")
                            v-progress-circular(v-if="podStatus(item) === 'pending'" indeterminate size="16" width="2" color="grey" class="mr-2")
                            v-icon(v-else-if="podStatus(item) === 'error'" left small) mdi-alert-circle
                            v-icon(v-else left small) mdi-open-in-new
                            | {{ linkLabel(item) }}
                      span(v-if="item.pods && item.pods.length")
                        div(v-for="pod in item.pods" :key="pod.name") {{ pod.name }}: {{ pod.status }} ({{ pod.ready }}, restarts: {{ pod.restarts }})
                      span(v-else) No pods found
                    v-btn(color="green" outlined class="ma-1" :loading="isFinishing(item)" @click="openFinishDialog(item)")
                      v-icon(left small) mdi-check-circle-outline
                      | Finish Interaction
              v-list-item(v-else)
                v-list-item-content
                  v-list-item-title.grey--text No applications requesting your input.
        v-expansion-panel
          v-expansion-panel-header
            div
              .text-subtitle-1.font-weight-medium Applications
              .text-caption.grey--text These are applications which are installed project wide for project {{ selectedProject.name }}.
          v-expansion-panel-content
            .d-flex.align-center.justify-end.mb-2
              span.text-caption.mr-2 Sort by:
              v-btn-toggle(v-model="sortKey" mandatory dense)
                v-btn(value="name" small) Name
                v-btn(value="startedAt" small) Started
              v-btn.ml-2(icon small @click="sortDesc = !sortDesc")
                v-icon {{ sortDesc ? 'mdi-sort-descending' : 'mdi-sort-ascending' }}
            v-progress-linear(v-if="loadingProject" indeterminate)
            v-list(v-else two-line)
              template(v-if="sortedApps(projectApplications).length")
                v-list-item(v-for="item in sortedApps(projectApplications)" :key="item.releaseName")
                  v-list-item-icon.align-self-center
                    v-icon mdi-application
                  v-list-item-content
                    v-list-item-title.font-weight-bold {{ item.name }}
                    v-list-item-subtitle Started {{ item.createdAt }}
                  .d-flex.align-center.flex-wrap
                    v-tooltip(right)
                      template(v-slot:activator="{ on, attrs }")
                        span(v-bind="attrs" v-on="on")
                          v-btn(v-for="path in item.paths" :key="path" outlined :color="linkColor(item)" class="ma-1" @click="onLinkClick(item, path)")
                            v-progress-circular(v-if="podStatus(item) === 'pending'" indeterminate size="16" width="2" color="grey" class="mr-2")
                            v-icon(v-else-if="podStatus(item) === 'error'" left small) mdi-alert-circle
                            v-icon(v-else left small) mdi-open-in-new
                            | {{ linkLabel(item) }}
                      span(v-if="item.pods && item.pods.length")
                        div(v-for="pod in item.pods" :key="pod.name") {{ pod.name }}: {{ pod.status }} ({{ pod.ready }}, restarts: {{ pod.restarts }})
                      span(v-else) No pods found
              v-list-item(v-else)
                v-list-item-content
                  v-list-item-title.grey--text No applications installed.

      v-dialog(v-model="dialog" max-width="480")
        v-card(v-if="dialogItem")
          v-card-title
            v-progress-circular(v-if="dialogStatus === 'pending'" indeterminate size="24" width="3" color="primary")
            v-icon(v-else-if="dialogStatus === 'error'" color="red") mdi-alert-circle
            v-icon(v-else color="green") mdi-check-circle
            span.ml-3 {{ dialogStatus === 'error' ? 'Problem starting the application' : (dialogStatus === 'ready' ? 'Application is ready' : 'Application is starting') }}
          v-card-text
            template(v-if="dialogStatus === 'pending'")
              p The application "{{ dialogItem.name }}" is still starting and may take some more time. Visiting it now is possible but might show errors until it is ready.
            template(v-else-if="dialogStatus === 'error'")
              p Unfortunately there is an issue starting the application "{{ dialogItem.name }}".
              div.mb-3(v-if="problemPods(dialogItem).length")
                div(v-for="pod in problemPods(dialogItem)" :key="pod.name") {{ pod.name }}: {{ pod.status }} ({{ pod.ready }}, restarts: {{ pod.restarts }})
              p Please reach out to the operator of this instance. Visiting the application anyway could show errors.
            template(v-else)
              p The application "{{ dialogItem.name }}" is now ready.
          v-card-actions
            v-spacer
            v-btn(text @click="dialog = false") {{ dialogStatus === 'error' ? 'Ok' : (dialogStatus === 'pending' ? 'Back' : 'Cancel') }}
            v-btn(color="primary" @click="visitDialogPath") {{ dialogStatus === 'ready' ? 'Visit' : 'Visit anyway' }}

      v-dialog(v-model="finishDialog" max-width="480")
        v-card
          v-card-title Finish interaction?
          v-card-text
            p Is the work in this step done? Finishing the interaction will close this application and continue the workflow.
          v-card-actions
            v-spacer
            v-btn(text @click="finishDialog = false") Back
            v-btn(color="green" @click="confirmFinish") Yes

      v-dialog(v-model="finishErrorDialog" max-width="480")
        v-card
          v-card-title
            v-icon(color="red") mdi-alert-circle
            span.ml-3 Could not finish interaction
          v-card-text
            p Could not finish interaction on "{{ finishErrorName }}", please retry or contact the sites operator.
            p.text-caption.grey--text error: {{ finishErrorMessage }}
          v-card-actions
            v-spacer
            v-btn(text @click="finishErrorDialog = false") Ok
</template>

<script lang="ts">
import Vue from "vue";
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";
import IdleTracker from "@/components/IdleTracker.vue";

export default Vue.extend({
  components: {
    IdleTracker,
  },
  data: () => ({
    loadingTriggered: true,
    loadingProject: true,
    projectApplications: [] as any,
    triggeredApplications: [] as any,
    polling: 0,
    fetching: false,
    dialog: false,
    dialogReleaseName: "",
    dialogPath: "",
    finishDialog: false,
    finishItem: null as any,
    finishing: [] as string[],
    finished: [] as string[],
    finishErrorDialog: false,
    finishErrorName: "",
    finishErrorMessage: "",
    openPanels: [0, 1],
    sortKey: "name",
    sortDesc: false,
  }),
  mounted() {
    this.getActiveApplications();
    this.polling = window.setInterval(() => {
      this.getActiveApplications();
    }, 10000);
  },
  beforeDestroy() {
    window.clearInterval(this.polling);
  },
  computed: {
    ...mapGetters([
      "currentUser",
      "isAuthenticated",
      "commonData",
      "selectedProject",
    ]),
    // Re-derive the dialog's app from the freshly polled lists (not a snapshot),
    // so an open dialog updates live as the app moves pending -> ready/error.
    dialogItem(): any {
      if (!this.dialogReleaseName) return null;
      const all = [...this.projectApplications, ...this.triggeredApplications];
      return all.find((a: any) => a.releaseName === this.dialogReleaseName) || null;
    },
    dialogStatus(): string {
      return this.dialogItem ? this.podStatus(this.dialogItem) : "pending";
    },
  },
  methods: {
    // Classify an app into 'ready' | 'pending' | 'error' from its pods' kube status.
    // A pod counts as ready when it is completed, or running with all containers ready
    // (N/N); normal lifecycle states (pending, creating, initializing, terminating,
    // running-but-not-yet-ready) are 'pending'; anything else is treated as an error.
    podStatus(item: any) {
      const pods = item.pods || [];
      if (pods.length === 0) {
        return "pending";
      }
      const transient = [
        "pending",
        "containercreating",
        "podinitializing",
        "terminating",
      ];
      let hasError = false;
      let hasPending = false;
      for (const pod of pods) {
        const status = (pod.status || "").toLowerCase();
        const [readyCount, wantCount] = (pod.ready || "").split("/");
        if (status === "completed") {
          continue;
        }
        if (status === "running" && readyCount === wantCount) {
          continue;
        }
        if (
          status === "running" ||
          /^init:\d/.test(status) || // Init:0/2 is progress; Init:Error/OOMKilled are failures
          transient.includes(status)
        ) {
          hasPending = true;
        } else {
          hasError = true;
        }
      }
      if (hasError) return "error";
      if (hasPending) return "pending";
      return "ready";
    },

    // Sort a list of apps by the shared sort controls (name or start date).
    sortedApps(apps: any) {
      const key = this.sortKey;
      const dir = this.sortDesc ? -1 : 1;
      return [...apps].sort((a: any, b: any) => {
        let av: any;
        let bv: any;
        if (key === "startedAt") {
          av = new Date(a.startedAt).getTime();
          bv = new Date(b.startedAt).getTime();
        } else {
          av = (a.name || "").toLowerCase();
          bv = (b.name || "").toLowerCase();
        }
        if (av < bv) return -dir;
        if (av > bv) return dir;
        return 0;
      });
    },

    // Outlined "Open" button color: grey while starting, red on error, blue when ready.
    linkColor(item: any) {
      const status = this.podStatus(item);
      if (status === "pending") return "grey";
      if (status === "error") return "red";
      return "primary";
    },

    // Button label mirrors the state: starting / error / ready.
    linkLabel(item: any) {
      const status = this.podStatus(item);
      if (status === "pending") return "Starting...";
      if (status === "error") return "Error";
      return "Open";
    },

    // Ready apps open in a new tab; otherwise show the status dialog.
    onLinkClick(item: any, path: string) {
      if (this.podStatus(item) === "ready") {
        window.open(path, "_blank");
        return;
      }
      this.dialogReleaseName = item.releaseName;
      this.dialogPath = path;
      this.dialog = true;
    },

    visitDialogPath() {
      window.open(this.dialogPath, "_blank");
      this.dialog = false;
    },

    // Confirm before finishing a workflow-triggered interaction.
    openFinishDialog(item: any) {
      this.finishItem = item;
      this.finishDialog = true;
    },

    confirmFinish() {
      this.finishDialog = false;
      this.finishInteraction(this.finishItem);
    },

    // Whether this app's finish request is currently in flight.
    isFinishing(item: any) {
      return this.finishing.includes(item.releaseName);
    },

    // Pods that are neither completed nor running-and-ready, i.e. the ones to surface as the error detail.
    problemPods(item: any) {
      const pods = item.pods || [];
      return pods.filter((pod: any) => {
        const status = (pod.status || "").toLowerCase();
        const [readyCount, wantCount] = (pod.ready || "").split("/");
        if (status === "completed") return false;
        if (status === "running" && readyCount === wantCount) return false;
        return true;
      });
    },

    getActiveApplications() {
      if (this.fetching) return;
      this.fetching = true;
      kaapanaApiService
        .helmApiGet("/active-applications", {})
        .then((response: any) => {
          const selectedProjectId = (this as any).$store.getters.selectedProject.id;
          // filter and format ingress routes
          const allActiveApplications = response.data
            .filter((item: any) => {
              // sanity check: ingress should have a path
              if (item.paths.length == 0) {
                console.log("WARNING: ignoring application without paths:", item);
                return false;
              }
              return true;
            })
            .map((item: any) => {
              let name = item.name;
              if ("kaapana.ai/display-name" in item.annotations) {
                name = item.annotations["kaapana.ai/display-name"];
              }
              // format the date
              const formattedDate = new Intl.DateTimeFormat('en-UK', {
                dateStyle: 'long',
                timeStyle: 'short',
              }).format(new Date(item.created_at));
              return {
                annotations: item.annotations,
                createdAt: formattedDate,
                startedAt: item.created_at,
                fromWorkflowRun: item.from_workflow_run,
                name: name,
                paths: item.paths,
                pods: item.pods,
                project: item.project,
                ready: item.ready,
                releaseName: item.release_name,
              };
            });
          // get applications that are triggered from workflow runs, scoped to the selected project
          this.triggeredApplications = allActiveApplications.filter((item: any) => {
            return item.fromWorkflowRun === true && item.project === selectedProjectId && !this.finished.includes(item.releaseName);
          });
          // get applications that are not triggered from a workflow run and includes current project name in all paths
          this.projectApplications = allActiveApplications.filter((item: any) => {
            const rulePattern = new RegExp(
              `^\/applications\/project\/${selectedProjectId}\/release\/.+$`
            );
            let hasProjectURL = item.paths.every((path: string) => {
              return rulePattern.test(path);
            });
            return hasProjectURL && (item.fromWorkflowRun === false);
          });
          this.loadingProject = false;
          this.loadingTriggered = false;
          this.fetching = false;
        })
        .catch((err: any) => {
          console.log(err);
          this.loadingProject = false;
          this.loadingTriggered = false;
          this.fetching = false;
        });
    },

    // Finish a single interaction without reloading the whole list: spin the
    // item's Finish button (and grey its Open button) via `finishing`, then on
    // success drop it from the list and remember it in `finished` so the 2s poll
    // can't re-add it before the backend uninstall completes. On failure, clear
    // the finishing state (resetting the item to its default look) and surface
    // the error in a dialog.
    finishInteraction(item: any) {
      const releaseName = item.releaseName;
      this.finishing.push(releaseName);
      kaapanaApiService
        .helmApiPost("/complete-active-application", { release_name: releaseName })
        .then(() => {
          this.finished.push(releaseName);
          this.triggeredApplications = this.triggeredApplications.filter(
            (app: any) => app.releaseName !== releaseName
          );
          this.finishing = this.finishing.filter((r: string) => r !== releaseName);
        })
        .catch((err: any) => {
          console.log(err);
          this.finishing = this.finishing.filter((r: string) => r !== releaseName);
          this.finishErrorName = item.name;
          this.finishErrorMessage =
            err?.response?.data?.detail ?? err?.response?.data ?? err?.message ?? String(err);
          this.finishErrorDialog = true;
        });
    },
  },
});
</script>

<style lang="scss">
a {
  text-decoration: none;
}
</style>
