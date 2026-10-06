import { kaapanaApiService } from '@kaapana/base-ui'

export interface AllowedDataset {
  name: string
  access_level?: string
}

export interface KaapanaInstance {
  id: number
  instance_name: string
  protocol: string
  host: string
  port: number
  token: string
  fernet_key: string
  ssl_check: boolean
  sync_timeout: number
  remote: boolean
  automatic_update: boolean
  automatic_workflow_execution: boolean
  allowed_dags: string[] | null
  allowed_datasets: AllowedDataset[] | null
  time_created: string
  time_updated: string
}

export interface RemoteInstanceDefinition {
  instance_name: string
  host: string
  port: number
  token: string
  fernet_key: string
  ssl_check: boolean
  sync_timeout?: number
}

export const SYNC_TIMEOUT_DEFAULT = 15
export const SYNC_TIMEOUT_MAX = 300

export function syncTimeoutRule(value: unknown) {
  const seconds = Number(value)
  return (
    (Number.isInteger(seconds) && seconds >= 1 && seconds <= SYNC_TIMEOUT_MAX) ||
    `Enter a whole number of seconds between 1 and ${SYNC_TIMEOUT_MAX}, for example ${SYNC_TIMEOUT_DEFAULT}.`
  )
}

export interface LocalInstanceSettings {
  ssl_check: boolean
  fernet_encrypted: boolean
  automatic_update: boolean
  automatic_workflow_execution: boolean
  allowed_dags: string[]
  allowed_datasets: string[]
}

export interface DatasetOption {
  name: string
  access_level: string
}

export const FERNET_DEACTIVATED = 'deactivated'

export async function listInstances(): Promise<KaapanaInstance[]> {
  const response: any = await kaapanaApiService.federatedClientApiPost('/get-kaapana-instances')
  return response.data
}

export async function checkForRemoteUpdates(): Promise<void> {
  await kaapanaApiService.federatedClientApiGet('/check-for-remote-updates')
}

export async function addRemoteInstance(definition: RemoteInstanceDefinition): Promise<void> {
  await kaapanaApiService.federatedClientApiPost('/remote-kaapana-instance', definition)
}

export async function updateRemoteInstance(definition: RemoteInstanceDefinition): Promise<void> {
  await kaapanaApiService.federatedClientApiPut('/remote-kaapana-instance', definition)
}

export async function updateLocalInstance(settings: LocalInstanceSettings): Promise<void> {
  await kaapanaApiService.federatedClientApiPut('/client-kaapana-instance', settings)
}

export async function deleteInstance(id: number): Promise<void> {
  await kaapanaApiService.federatedClientApiDelete('/kaapana-instance', { kaapana_instance_id: id })
}

export async function listDags(instanceName: string): Promise<string[]> {
  const response: any = await kaapanaApiService.federatedClientApiPost('/get-dags', {
    instance_names: [instanceName],
    kind_of_dags: 'all',
  })
  return response.data
}

export async function listProjectDatasets(): Promise<DatasetOption[]> {
  const response: any = await kaapanaApiService.federatedClientApiGet('/datasets', {
    skip_identifiers: true,
  })
  return (response.data as DatasetOption[]).filter((dataset) => dataset.access_level === 'project')
}

export function instanceDefinition(instance: KaapanaInstance): RemoteInstanceDefinition {
  return {
    instance_name: instance.instance_name,
    host: instance.host,
    port: instance.port,
    token: instance.token,
    fernet_key: instance.fernet_key,
    ssl_check: instance.ssl_check,
  }
}
