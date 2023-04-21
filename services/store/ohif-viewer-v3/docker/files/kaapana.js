var hostname = window.location.href.split("//")[1].split("/")[0];
console.log("Hostname: " + hostname);
window.config = {
  // default: '/'
  routerBasename: "/ohif-v3/",
  extensions: [],
  modes: [],
  showStudyList: true,
  dataSources: [
    {
      friendlyName: "KAAPANA",
      namespace: "@ohif/extension-default.dataSourcesModule.dicomweb",
      sourceName: "dicomweb",
      configuration: {
        name: "DCM4CHEE",
        wadoUriRoot: "https://" + hostname + "/dcm4chee-arc/aets/KAAPANA/wado",
        qidoRoot: "https://" + hostname + "/dcm4chee-arc/aets/KAAPANA/rs",
        wadoRoot: "https://" + hostname + "/dcm4chee-arc/aets/KAAPANA/rs",
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
