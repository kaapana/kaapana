import Vue from "vue";
import httpClient from '@/common/httpClient';

import { TRIGGER_DOWNLOAD_TRACKER } from "@/store/actions.type";
import { SET_DOWNLOAD_DAG_ID } from '@/store/mutations.type'

const defaults = {
    downloadDagId: "",
    downloadWorkflowName: "",
    downloadRunId: "",
    downloadStarted: false,
    downloadCompleted: false,
    downloadReady: false,
    downloadMessage: "",
    downloadUrl: "",
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
    downloadUrl(state: any) {
      return state.downloadUrl
    }
}

const actions = {
    [TRIGGER_DOWNLOAD_TRACKER](context: any, payload: any) {
        console.log(payload.workflowName);
        context.commit(SET_DOWNLOAD_DAG_ID, payload.dagId);
    },
}

const mutations = {
    [SET_DOWNLOAD_DAG_ID](state: any, dagId: string) {
        state.downloadDagId = dagId
    },
    // [SET_DOWNLOAD_WORKFLOW_NAME](state: any, dagId: string) {
    //     state.downloadDagId = dagId
    // },
}

export default {
    state,
    actions,
    mutations,
    getters,
}