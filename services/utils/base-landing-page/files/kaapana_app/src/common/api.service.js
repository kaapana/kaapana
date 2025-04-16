import Vue from "vue";
import httpClient, {httpClientWithoutTimeout} from "./httpClient";
import store from '../store/index';

const KAAPANA_BACKEND_ENDPOINT = process.env.VUE_APP_KAAPANA_BACKEND_ENDPOINT;

const updateDataset = async (body) => {
  return await httpClient.put(
    KAAPANA_BACKEND_ENDPOINT + "client/dataset",
    body
  );
};

const createDataset = async (body) => {
  return await httpClient.post(
    KAAPANA_BACKEND_ENDPOINT + "client/dataset",
    body
  );
};

const deleteDataset = async (datasetName) => {
  try {
    const res = await httpClient.delete(
      KAAPANA_BACKEND_ENDPOINT +
        `client/dataset?name=${encodeURIComponent(datasetName)}`
    );
    return res.data["ok"];
  } catch (error) {
    Vue.notify({
      title: "Error",
      text:
        error.response && error.response.data && error.response.data.detail
          ? error.response.data.detail
          : error,
      type: "error",
    });
  }
};

const loadDatasetByName = async (datasetName) => {
  try {
    const dataset = (
      await httpClient.get(
        KAAPANA_BACKEND_ENDPOINT +
          `client/dataset?name=${encodeURIComponent(datasetName)}`
      )
    ).data;
    return dataset;
  } catch (error) {
    Vue.notify({
      title: "Error",
      text:
        error.response && error.response.data && error.response.data.detail
          ? error.response.data.detail
          : error,
      type: "error",
    });
  }
};

const loadDatasets = async (namesOnly = true) => {
  try {
    const datasets = await httpClient.get(
      KAAPANA_BACKEND_ENDPOINT + "client/datasets"
    );
    if (namesOnly) {
      return datasets.data.map((dataset) => dataset.name);
    } else {
      return datasets.data;
    }
  } catch (error) {
    Vue.notify({
      title: "Error",
      text:
        error.response && error.response.data && error.response.data.detail
          ? error.response.data.detail
          : error,
      type: "error",
    });
  }
};

const loadSeriesData = async (seriesInstanceUID) => {
  try {
    const response = await httpClient.get(
      KAAPANA_BACKEND_ENDPOINT + `dataset/series/${seriesInstanceUID}`
    );
    return response.data;
  } catch (error) {
    Vue.notify({
      title: "Error",
      text:
        error.response && error.response.data && error.response.data.detail
          ? error.response.data.detail
          : error,
      type: "error",
    });
    throw error;
  }
};

const loadSeriesEmbeddings = async (seriesInstanceUID) => {
  try {
    const response = await httpClient.get(
      KAAPANA_BACKEND_ENDPOINT + `dataset/series/${seriesInstanceUID}/embeddings`
    );
    return response.data;
  } catch (error) {
    Vue.notify({
      title: "Error",
      text:
        error.response && error.response.data && error.response.data.detail
          ? error.response.data.detail
          : error,
      type: "error",
    });
    throw error;
  }
};   

const loadPatients = async (data) => {
  try {
    const res = await httpClient.post(
      KAAPANA_BACKEND_ENDPOINT + "dataset/series",
      data
    );
    return res.data;
  } catch (error) {
    Vue.notify({
      title: "Error",
      text:
        error.response && error.response.data && error.response.data.detail
          ? error.response.data.detail
          : error,
      type: "error",
    });
    throw error;
  }
};

const getAggregatedSeriesNum = async (data) => {
  try {
    const res = await httpClient.post(
      KAAPANA_BACKEND_ENDPOINT + "dataset/aggregatedSeriesNum",
      data
    );
    return res.data;
  } catch (error) {
    Vue.notify({
      title: "Error",
      text:
        error.response && error.response.data && error.response.data.detail
          ? error.response.data.detail
          : error,
      type: "error",
    });
    throw error;
  }
};

const loadFieldNames = async () => {
  try {
    return await httpClient.get(
      KAAPANA_BACKEND_ENDPOINT + "dataset/field_names"
    );
  } catch (error) {
    Vue.notify({
      title: "Error",
      text:
        error.response && error.response.data && error.response.data.detail
          ? error.response.data.detail
          : error,
      type: "error",
    });
    throw error;
  }
};

const loadValues = async (key, query = {}) => {
  try {
    return await httpClient.post(
      KAAPANA_BACKEND_ENDPOINT +
        `dataset/query_values/${encodeURIComponent(key)}`,
      query
    );
  } catch (error) {
    Vue.notify({
      title: "Error",
      text:
        error.response && error.response.data && error.response.data.detail
          ? error.response.data.detail
          : error,
      type: "error",
    });
  }
};

const updateTags = async (data) => {
  const response = await httpClient.post(
    KAAPANA_BACKEND_ENDPOINT + "dataset/tag",
    data
  );
  // TODO: ideally this should return the new tags which are then assigned
};

const loadDashboard = async (seriesInstanceUIDs, fields, query = {}) => {
  return (
    await httpClient.post(KAAPANA_BACKEND_ENDPOINT + "dataset/dashboard", {
      series_instance_uids: seriesInstanceUIDs,
      names: fields,
      query: query
    })
  ).data;
};

const loadDicomTagMapping = async () => {
  return (await httpClient.get(KAAPANA_BACKEND_ENDPOINT + "dataset/fields"))
    .data;
};

const downloadDatasets = async (concatenatedSeriesUIDs) => {
  try {
    const encodedSeriesUIDs = encodeURIComponent(concatenatedSeriesUIDs);
    const response = await httpClientWithoutTimeout.get(
      KAAPANA_BACKEND_ENDPOINT + `dataset/download?series_uids=${encodedSeriesUIDs}`,
      { responseType: 'blob' }  // Important for file downloads
    );

    // Create a download link for the received blob
    const blob = new Blob([response.data], { type: response.headers['content-type'] });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);

    // Extract filename from headers or define a fallback
    const contentDisposition = response.headers['content-disposition'];
    const fileName = contentDisposition
      ? contentDisposition.split('filename=')[1].replace(/"/g, '')
      : 'kaapana_datasets_download.zip'; // Default file name

    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();

    // Cleanup
    URL.revokeObjectURL(link.href);
    document.body.removeChild(link);

  } catch (error) {
    if (error.response && error.response.data) {
      // Convert blob error response to JSON
      const reader = new FileReader();
      reader.onload = function () {
        let errorText = ""
        try {
          const errorJson = JSON.parse(reader.result);
          errorText = 'Download failed:' + errorJson.detail;
        } catch (parseError) {
          errorText ='Failed to parse error response:' + parseError;
        }
        Vue.notify({
          title: "Download Error",
          text: errorText,
          type: "error",
        });        
      };
      reader.readAsText(error.response.data);
    } else {
      console.error('Unexpected error:', error);
    }

    throw error;
  }
};

const fetchProjects = async () => {
  const currentUser = store.getters.currentUser
  try {
    if (currentUser.roles.includes("admin")) {
      return (await httpClient.get("/aii/projects")).data;
    } else {
      return (await httpClient.get("/aii/users/" + currentUser.id + "/projects")).data
    }
    
  } catch (error) {
    Vue.notify({
      title: "Error",
      text:
        error.response && error.response.data && error.response.data.detail
          ? error.response.data.detail
          : error,
      type: "error",
    });
  }
};

export {
  updateTags,
  loadPatients,
  loadSeriesData,
  loadSeriesEmbeddings,
  createDataset,
  updateDataset,
  deleteDataset,
  loadDatasets,
  loadDatasetByName,
  loadDashboard,
  loadDicomTagMapping,
  loadFieldNames,
  loadValues,
  getAggregatedSeriesNum,
  fetchProjects,
  downloadDatasets
};
