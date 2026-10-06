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

/** How the shell picks the theme: follow the browser, or a fixed choice. */
export type ThemeMode = 'system' | 'light' | 'dark'

export interface Settings {
  /** The effective value the views read; the shell derives it from themeMode. */
  darkMode: boolean
  themeMode: ThemeMode
  devMode: boolean
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
