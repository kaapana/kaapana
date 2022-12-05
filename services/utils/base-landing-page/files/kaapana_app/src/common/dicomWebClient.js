import * as DICOMwebClient from "dicomweb-client";

const dicomWebClient = new DICOMwebClient.api.DICOMwebClient({
  url: process.env.VUE_APP_RS_ENDPOINT
})


export default dicomWebClient;
