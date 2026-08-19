var hostname=window.location.href.split("//")[1].split("/")[0]
console.log("Hostname: "+hostname)

// The viewer URL decides the project scope: served under
// /project/<id>/slim (the portal-ui shell links it that way), DICOMweb
// requests target the project-scoped dicom-web-filter route. Without the
// prefix the plain, unscoped route is used.
var projectPrefix = (window.location.pathname.match(/^\/project\/[^/]+/) || [""])[0];
console.log("Project prefix: " + (projectPrefix || "(none)"));

window.config = {
  path: projectPrefix + "/slim",
  /** This is an array, but we'll only use the first entry for now */
  servers: [
    {
      id: "local",
      url: "https://"+hostname+projectPrefix+"/dicom-web-filter",
      write: true
    }
  ],
  renderer:
  {
    retrieveRendered: false
  },
  disableWorklist: false,
  disableAnnotationTools: false,
  annotations: [
    {
      finding: {
        value: '108369006',
        schemeDesignator: 'SCT',
        meaning: 'Tumor'
      },
      style: {
        stroke: {
          color: [251, 134, 4, 1],
          width: 2
        },
        fill: {
          color: [255, 255, 255, 0.2]
        }
      }
    },
    {
      finding: {
        value: '85756007',
        schemeDesignator: 'SCT',
        meaning: 'Tissue'
      },
      style: {
        stroke: {
          color: [51, 204, 51, 1],
          width: 2
        },
        fill: {
          color: [255, 255, 255, 0.2]
        }
      }
    }
  ]
};