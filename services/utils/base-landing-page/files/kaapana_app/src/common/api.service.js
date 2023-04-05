/* eslint-disable */


import Vue from "vue";
import dicomWebClient from "./dicomWebClient";
import httpClient from "./httpClient";

const WADO_ENDPOINT = process.env.VUE_APP_WADO_ENDPOINT
const KAAPANA_BACKEND_ENDPOINT = process.env.VUE_APP_KAAPANA_BACKEND_ENDPOINT

const deleteSeriesFromPlatform = async (seriesInstanceUID, dag_id = 'delete-series-from-platform') => {
    return await httpClient.post(
        KAAPANA_BACKEND_ENDPOINT + 'client/job',
        {
            "dag_id": dag_id,
            "conf_data": {
                "data_form": {
                    "identifiers": [
                        seriesInstanceUID
                    ]
                },
                "form_data": {
                    "delete_complete_study": false,
                    "single_execution": false
                }
            },
            "kaapana_instance_id": 1 // TODO: this should rather be set by the backend
        }
    )
}

const updateDataset = async (body) => {
    return await httpClient.put(KAAPANA_BACKEND_ENDPOINT + 'client/dataset', body)
}

const createDataset = async (body) => {
    return await httpClient.post(KAAPANA_BACKEND_ENDPOINT + 'client/dataset', body)
}
const loadDatasets = async () => {
    try {
        // TODO
        const datasets = (
            await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'client/datasets')
        )
        return datasets.data
    } catch (error) {
        Vue.notify({title: 'Network/Server error', text: error, type: 'error'});
    }
}

const loadDatasetByName = async (datasetName) => {
    try {
        const dataset = (
            await httpClient.get(KAAPANA_BACKEND_ENDPOINT + `client/dataset?name=${datasetName}`)
        ).data
        return dataset
    } catch (error) {
        Vue.notify({title: 'Network/Server error', text: error, type: 'error'});
    }
}

const loadDatasetNames = async () => {
    try {
        const datasets = (
            await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'client/datasets')
        )
        return datasets.data.map(dataset => dataset.name)
    } catch (error) {
        Vue.notify({title: 'Network/Server error', text: error, type: 'error'});
    }
}


const loadSeriesData = async (seriesInstanceUID) => {
    try {
        const response = (await httpClient.get(
            KAAPANA_BACKEND_ENDPOINT + `dataset/series/${seriesInstanceUID}`
        ))
        return response.data
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

const loadSeriesMetaData = async (studyInstanceUID, seriesInstanceUID) => {
    // TODO: should also able to be unified (at least partially)
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

const loadPatients = async (data) => {
    try {
        const res = await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'dataset/series?body=' + JSON.stringify(data))
        return res.data
    } catch (error) {
        Vue.notify({title: 'Network/Server error', text: error.text, type: 'error'});
        throw error
    }
}

const loadAvailableTags = async (body = {}) => {
    try {
        return (
            await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'dataset/query_values?query=' + JSON.stringify(body))
        )
    } catch (error) {
        Vue.notify({title: 'Network/Server error', text: error, type: 'error'});
    }
}


const updateTags = async (data) => {
    const response = await httpClient.post(KAAPANA_BACKEND_ENDPOINT + 'dataset/tag', data)
    // TODO: ideally this should return the new tags which are then assigned
}

const loadDashboard = async (seriesInstanceUIDs, fields) => {
    return (await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'dataset/dashboard?config=' + JSON.stringify({
        series_instance_uids: seriesInstanceUIDs,
        names: fields
    }))).data

}

const loadDicomTagMapping = async () => {
    return (await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'dataset/fields')).data
}


export {
    updateTags,
    loadDicom,
    assembleWadoURI,
    loadSeriesMetaData,
    loadPatients,
    loadAvailableTags,
    loadSeriesData,
    createDataset,
    loadDatasets,
    deleteSeriesFromPlatform,
    updateDataset,
    loadDatasetNames,
    loadDatasetByName,
    loadDashboard,
    loadDicomTagMapping
}
