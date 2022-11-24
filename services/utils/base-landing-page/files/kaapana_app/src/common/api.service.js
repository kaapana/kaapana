/* eslint-disable */


import httpClient from './httpClient';
import Vue from "vue";
import dicomWebClient from "./dicomWebClient";
import axios from "axios";

const WADO_ENDPOINT = process.env.VUE_APP_WADO_ENDPOINT
const RS_ENDPOINT = process.env.VUE_APP_RS_ENDPOINT
const KAAPANA_FLOW_ENDPOINT = process.env.VUE_APP_KAAPANA_FLOW_ENDPOINT
const KAAPANA_BACKEND_ENDPOINT = process.env.VUE_APP_KAAPANA_BACKEND_ENDPOINT

// TODO: add a wrapper for notifying when error and maybe reloading

const updateTags = async (data) => {
    const response = await httpClient.post(KAAPANA_FLOW_ENDPOINT + '/tag', data)
    // TODO: ideally this should return the new tags which are then assigned
}

const formatMetadata = async (data) => {
    return await httpClient.post(KAAPANA_FLOW_ENDPOINT + '/curation_tool/format_metadata', data)
}

const deleteSeriesFromPlatform = async (seriesInstanceUID, dag_id = 'delete-series-from-platform') => {
    return await httpClient.post(KAAPANA_FLOW_ENDPOINT + '/trigger/' + dag_id,
        {
            "data_form": {
                "cohort_identifiers": [
                    seriesInstanceUID
                ],
                "cohort_query": {
                    'index': 'meta-index'
                }
            },
            "form_data": {
                "delete_complete_study": false,
                "single_execution": false
            }
        })
}

const updateCohort = async (body) => {
    return await httpClient.put(KAAPANA_BACKEND_ENDPOINT + '/cohort', body)
}

const loadCohorts = async () => {
    try {
        // TODO
        const cohorts = (
            await httpClient.get(KAAPANA_BACKEND_ENDPOINT + '/cohorts')
        )
        return cohorts.data.map(cohort => ({
            name: cohort.cohort_name,
            identifiers: cohort.cohort_identifiers
        }))
    } catch (error) {
        Vue.notify({title: 'Network/Server error', text: error, type: 'error'});
    }
}

const loadCohortNames = async () => {
    try {
        const cohorts = (
            await httpClient.get(KAAPANA_BACKEND_ENDPOINT + '/cohort-names')
        )
        return cohorts.data
    } catch (error) {
        Vue.notify({title: 'Network/Server error', text: error, type: 'error'});
    }
}


const loadSeriesFromMeta = async (seriesInstanceUID) => {
    try {
        const response = (await httpClient.get(
            KAAPANA_FLOW_ENDPOINT + `/curation_tool/seriesInstanceUID/${seriesInstanceUID}`
        ))
        const data = response.data

        if (
            data['0020000D StudyInstanceUID_keyword'] === undefined ||
            data["0020000E SeriesInstanceUID_keyword"] === undefined ||
            data['00080060 Modality_keyword'] === undefined ||
            data === undefined ||
            data['dataset_tags_keyword'] === undefined
        ) {
            Vue.notify(
                {
                    title: 'Invalid Data',
                    text: `Received invalid data for ${seriesInstanceUID}`,
                    type: 'error'
                }
            )
        }

        return {
            src: RS_ENDPOINT +
                `/studies/${data['0020000D StudyInstanceUID_keyword']}/` +
                `series/${data["0020000E SeriesInstanceUID_keyword"]}/` +
                `thumbnail?viewport=300,300`,
            seriesDescription: data['0008103E SeriesDescription_keyword'] || "",
            modality: data['00080060 Modality_keyword'],
            seriesData: data,
            tags: data['dataset_tags_keyword'],
        }

    } catch (error) {
        Vue.notify({title: 'Network/Server error', text: error, type: 'error'});
    }
}

const assembleWadoURI = (studyUID, seriesUID, objectUID) => {
    return WADO_ENDPOINT
        + '?requestType=WADO'
        + `&studyUID=${studyUID}`
        + `&seriesUID=${seriesUID}`
        + `&objectUID=${objectUID}`
        + '&contentType=application/dicom'
}

const loadDicom = async (studyUID, seriesUID, objectUID) => {
    return (await httpClient.get(
        assembleWadoURI(studyUID, seriesUID, objectUID),
        {
            responseType: "arraybuffer"
        }
    )).data
}

const loadMetaData = async (studyUID, seriesUID) => {
    return (await httpClient.get(
        RS_ENDPOINT +
        `/studies/${studyUID}/` +
        `series/${seriesUID}/` +
        `metadata`
    )).data
}

const loadSeriesMetaData = async (studyInstanceUID, seriesInstanceUID) => {
    const data = await dicomWebClient.retrieveSeriesMetadata({
        'studyInstanceUID': studyInstanceUID,
        'seriesInstanceUID': seriesInstanceUID
    })
    return {
        modality: data[0]['00080060']['Value'][0],
        studyInstanceUID: data[0]["0020000D"]["Value"][0],
        seriesInstanceUID: data[0]["0020000E"]["Value"][0],
        objectUID: data[0]["00080018"]["Value"][0],
        referenceSeriesInstanceUID: data[0]["00081115"] !== undefined // only seg objects
            ? data[0]["00081115"]["Value"][0]["0020000E"]["Value"][0]
            : '',
        imageIds: data
            .map(instance => ({
                'InstanceNumber': parseInt(instance['00200013']['Value']),
                'uri': 'wadouri: ' + assembleWadoURI(
                    instance["0020000D"]["Value"][0],
                    instance["0020000E"]["Value"][0],
                    instance["00080018"]["Value"][0]
                )
            }))
            .sort((a, b) => a['InstanceNumber'] - b['InstanceNumber'])
            .map(item => item['uri'])
    }
}

const loadPatients = async (url, data) => {
    return (
        await httpClient.post(KAAPANA_FLOW_ENDPOINT + '/curation_tool/' + url, data)
    ).data
}

const loadAvailableTags = async () => {
    try {
        return (
            await httpClient.get(KAAPANA_FLOW_ENDPOINT + '/curation_tool/query_values')
        )
    } catch (error) {
        Vue.notify({title: 'Network/Server error', text: error, type: 'error'});
    }
}


export {
    updateTags,
    loadSeriesFromMeta,
    loadDicom,
    assembleWadoURI,
    loadSeriesMetaData,
    loadPatients,
    loadAvailableTags,
    loadMetaData,
    loadCohorts,
    formatMetadata,
    deleteSeriesFromPlatform,
    updateCohort,
    loadCohortNames
}
