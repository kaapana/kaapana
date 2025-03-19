import Vue from "vue";
import httpClient from '@/common/httpClient';

import { TRIGGER_DOWNLOAD_TRACKER, CHECK_DOWNLOAD_STATUS } from "@/store/actions.type";
import { SET_DOWNLOAD_DAG_ID } from '@/store/mutations.type'

// const AIRFLOW_API_BASE_URL ='/flow/api/v1'
const KAAPANA_BACKEND_CLIENT ='/kaapana-backend/client'

const SET_DOWNLOAD_START = 'set_download_start_values'
const UPDATE_DOWNLOAD_TASK_COUNTS = 'update_download_task_counts'

const defaults = {
    downloadDagId: "",
    downloadWorkflowName: "",
    downloadRunId: "",
    downloadStarted: false,
    downloadCompleted: false,
    downloadReady: false,
    downloadMessage: "",
    downloadUrl: "",
    downloadTotalTasks: 0,
    downloadCompletedTasks: 0,
}

const state = Object.assign({}, defaults)

const getters = {
    downloadDagId(state: any) {
      return state.downloadDagId
    },
    downloadCompleted(state: any) {
      return state.downloadCompleted
    },
    downloadStarted(state: any) {
      return state.downloadStarted
    },
    downloadSuccess(state: any) {
      return state.downloadSuccess
    },
    downloadMessage(state: any) {
      return state.downloadMessage
    },
    downloadTotalTasks(state: any) {
      return state.downloadTotalTasks
    },
    downloadCompletedTasks(state: any) {
      return state.downloadCompletedTasks
    },
    downloadUrl(state: any) {
      return state.downloadUrl
    },

}

const actions = {
    [TRIGGER_DOWNLOAD_TRACKER](context: any, payload: any) {
        httpClient.get(`${KAAPANA_BACKEND_CLIENT}/jobs?workflow_name=${payload.workflowName}`).then((response: any) => {
            const allJobs = response.data;
            let found = false;
            if (allJobs.length > 0) {
              const job = allJobs[0];
              payload.runId = job['run_id'];
              context.commit(SET_DOWNLOAD_START, payload);
              found = true;
            }

            if (!found) {
                console.error(`Failed to connect download workflow. Workflow with the name ${payload.workflowName} not found.`)
            }
          }).catch((error: any) => {
            console.error("Error fetching all runs:", error);
          })
    },
    [CHECK_DOWNLOAD_STATUS](context: any) {
      return new Promise((resolve: any) => {
        httpClient.get(`${KAAPANA_BACKEND_CLIENT}/jobs?workflow_name=${state.downloadWorkflowName}`).then((response: any) => {
          const allJobs = response.data;
          if (allJobs.length > 0) {
            const job = allJobs[0];
            const jobDesc = job['description'];
            
            if (jobDesc) {
              let parsed = JSON.parse(jobDesc.replace(/'/g, '"'));
              const tasks = Object.keys(parsed);
              let processed = 0
              for (let key in parsed) {
                if (parsed[key]['state'] == 'success' || parsed[key]['state'] == 'skipped') {
                  processed++;
                }
              }

              let payload = {total: tasks.length, completed: processed}
              context.commit(UPDATE_DOWNLOAD_TASK_COUNTS, payload);
            }
          }
        }).catch((error: any) => {
          console.error("Error fetching projects:", error);
          resolve(false)
        })
      })
    },
}

const mutations = {
    [SET_DOWNLOAD_DAG_ID](state: any, dagId: string) {
        state.downloadDagId = dagId
    },
    [SET_DOWNLOAD_START](state: any, payload: any) {
        state.downloadDagId = payload.dagId;
        state.downloadWorkflowName = payload.workflowName;
        state.downloadRunId = payload.runId;
        state.downloadStarted = true;
        state.downloadMessage = "Download Started";
    },
    [UPDATE_DOWNLOAD_TASK_COUNTS](state: any, payload: any) {
        state.downloadTotalTasks = payload.total;
        state.downloadCompletedTasks = payload.completed;
    },
}

export default {
    state,
    actions,
    mutations,
    getters,
}