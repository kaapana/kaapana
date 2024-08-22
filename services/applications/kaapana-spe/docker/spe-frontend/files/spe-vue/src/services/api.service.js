// import Vue from "vue";
import axios from "axios";

const KAAPANA_BACKEND_ENDPOINT = '/kaapana-backend/'
;

const loadDatasets = async (namesOnly = true) => {
  try {
    const datasets = await axios.get(
      KAAPANA_BACKEND_ENDPOINT + "client/datasets"
    );
    if (namesOnly) {
      return datasets.data.map((dataset) => dataset.name);
    } else {
      return datasets.data;
    }
  } catch (error) {
    // Vue.notify({
    //   title: "Error",
    //   text:
    //     error.response && error.response.data && error.response.data.detail
    //       ? error.response.data.detail
    //       : error,
    //   type: "error",
    // });
  }
};


export {
  loadDatasets
};
