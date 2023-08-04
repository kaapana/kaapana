import Vue from "vue";
import httpClient from "./httpClient";

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

const loadDashboard = async (seriesInstanceUIDs, fields) => {
  return (
    await httpClient.post(KAAPANA_BACKEND_ENDPOINT + "dataset/dashboard", {
      series_instance_uids: seriesInstanceUIDs,
      names: fields,
    })
  ).data;
};

const loadDicomTagMapping = async () => {
  return (await httpClient.get(KAAPANA_BACKEND_ENDPOINT + "dataset/fields"))
    .data;
};

export {
  updateTags,
  loadPatients,
  loadSeriesData,
  createDataset,
  updateDataset,
  deleteDataset,
  loadDatasets,
  loadDatasetByName,
  loadDashboard,
  loadDicomTagMapping,
  loadFieldNames,
  loadValues,
};
