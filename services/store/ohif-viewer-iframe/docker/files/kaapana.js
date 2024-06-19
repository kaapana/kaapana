var hostname = window.location.href.split("//")[1].split("/")[0];
console.log("Hostname: " + hostname);
window.config = {
  // default: '/'
  routerBasename: "/ohif-iframe/",
  extensions: [],
  modes: [],
  showStudyList: true,
  dataSources: [
    {
      friendlyName: "KAAPANA",
      namespace: "@ohif/extension-default.dataSourcesModule.dicomweb",
      sourceName: "dicomweb",
      configuration: {
        name: "DicomWebFilter",
        wadoUriRoot: "https://" + hostname + "/dicom-web-filter/wado",
        qidoRoot: "https://" + hostname + "/dicom-web-filter",
        wadoRoot: "https://" + hostname + "/dicom-web-filter",
        qidoSupportsIncludeField: true,
        supportsReject: true,
        imageRendering: "wadors",
        thumbnailRendering: "wadors",
        enableStudyLazyLoad: true,
        supportsFuzzyMatching: true,
        supportsWildcard: true,
      },
    },
  ],
  defaultDataSourceName: 'dicomweb',
};
