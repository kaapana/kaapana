export interface User {
  username: string
  roles: string[]
  groups: string[]
  id: string
}

export interface Project {
  id: string | number
  name: string
  short_id?: string
  access_level?: string
}

// series-instance-UIDs grouped study -> series
export type Studies = Record<string, string[]>
// patient -> study -> series
export type Patients = Record<string, Studies>

export interface Dataset {
  name: string
  access_level: string
  identifiers: string[]
  username?: string
  time_created?: string
  time_updated?: string
}
