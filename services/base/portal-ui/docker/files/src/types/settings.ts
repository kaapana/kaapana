// Shape of localStorage["settings"] shared with the extracted view containers.
// defaultUIConfig.ts provides the defaults.

export interface DatasetPropItem {
  name: string
  display: boolean
  truncate: boolean
  dashboard: boolean
  patientView?: boolean
  studyView?: boolean
}

export interface WorkflowFormDefaults {
  properties: { [key: string]: unknown }
  hideOnUI?: string[]
}

export interface Settings {
  darkMode: boolean
  devMode: boolean
  navigationMode: boolean
  landingPage: string[]
  datasets: {
    structured: boolean
    cols: string
    cardText: boolean
    tagBar: { multiple: boolean; tags: string[] }
    itemsPerPagePagination: number
    sort: string
    sortDirection: string
    executeSlicedSearch: boolean
    props: DatasetPropItem[]
  }
  workflows: { [dagName: string]: WorkflowFormDefaults }
  [key: string]: unknown
}
