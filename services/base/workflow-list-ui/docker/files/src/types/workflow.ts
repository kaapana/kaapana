export interface KaapanaInstance {
  instance_name: string
  remote?: boolean
  [key: string]: any
}

export interface Workflow {
  workflow_name: string
  workflow_id: string
  dataset_name: { name: string; access_level: string } | null
  time_created: string
  time_updated: string
  username: string
  kaapana_instance: KaapanaInstance
  status: string
  service_workflow?: boolean
  automatic_execution?: boolean
  workflow_jobs: string[]
  [key: string]: any
}

export interface Job {
  id: number | string
  status: string
  description?: string | null
  conf_data?: any
  time_created: string
  time_updated: string
  dag_id: string
  run_id: string
  kaapana_instance: KaapanaInstance
  owner_kaapana_instance_name: string
  external_job_id?: string | number | null
  service_job?: boolean
  [key: string]: any
}
