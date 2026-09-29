import { httpClient, httpClientWithoutTimeout } from '@kaapana/base-ui'
import type { Dataset } from '@/types'
import { isAxiosError } from 'axios'

const KAAPANA_BACKEND_ENDPOINT = import.meta.env.VITE_KAAPANA_BACKEND_ENDPOINT

const updateDataset = async (body: any) => {
  return await httpClient.put(KAAPANA_BACKEND_ENDPOINT + 'client/dataset', body)
}

const createDataset = async (body: any) => {
  return await httpClient.post(KAAPANA_BACKEND_ENDPOINT + 'client/dataset', body)
}

const deleteDataset = async (datasetName: string, accessLevel: string) => {
  const res = await httpClient.delete(KAAPANA_BACKEND_ENDPOINT + 'client/dataset', {
    params: { name: datasetName, access_level: accessLevel },
  })
  return res.data['ok']
}

const loadDatasetByName = async (datasetName: string, access_level = 'project') => {
  return (
    await httpClient.get(
      KAAPANA_BACKEND_ENDPOINT +
        `client/dataset?name=${encodeURIComponent(datasetName)}&access_level=${encodeURIComponent(access_level)}`,
    )
  ).data
}

const loadDatasets = async (skipIdentifiers = true): Promise<Dataset[]> => {
  const datasets = await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'client/datasets', {
    params: skipIdentifiers ? { skip_identifiers: true } : {},
  })
  return datasets.data
}

const loadSeriesData = async (seriesInstanceUID: string) => {
  const response = await httpClient.get(
    KAAPANA_BACKEND_ENDPOINT + `dataset/series/${seriesInstanceUID}`,
  )
  return response.data
}

const loadPatients = async (data: any) => {
  const res = await httpClient.post(KAAPANA_BACKEND_ENDPOINT + 'dataset/series', data)
  return res.data
}

const getAggregatedSeriesNum = async (data: any) => {
  const res = await httpClient.post(KAAPANA_BACKEND_ENDPOINT + 'dataset/aggregatedSeriesNum', data)
  return res.data
}

const loadFieldNames = async () => {
  return await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'dataset/field_names')
}

const loadValues = async (key: string, query: any = {}) => {
  return await httpClient.post(
    KAAPANA_BACKEND_ENDPOINT + `dataset/query_values/${encodeURIComponent(key)}`,
    query,
  )
}

const loadSearchFields = async () => {
  const response = await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'dataset/search_fields')
  return response.data
}

const updateTags = async (data: any) => {
  await httpClient.post(KAAPANA_BACKEND_ENDPOINT + 'dataset/tag', data)
  // TODO: ideally this should return the new tags which are then assigned
}

const loadDashboard = async (
  seriesInstanceUIDs: string[],
  fields: string[],
  query: any = {},
) => {
  return (
    await httpClient.post(KAAPANA_BACKEND_ENDPOINT + 'dataset/dashboard', {
      series_instance_uids: seriesInstanceUIDs,
      names: fields,
      query: query,
    })
  ).data
}

const loadDicomTagMapping = async () => {
  return (await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'dataset/fields')).data
}

const downloadDatasets = async (concatenatedSeriesUIDs: string) => {
  try {
    const encodedSeriesUIDs = encodeURIComponent(concatenatedSeriesUIDs)
    const response = await httpClientWithoutTimeout.get(
      KAAPANA_BACKEND_ENDPOINT + `dataset/download?series_uids=${encodedSeriesUIDs}`,
      { responseType: 'blob' },
    )

    const blob = new Blob([response.data], {
      type: (response.headers['content-type'] as string) || undefined,
    })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)

    const contentDisposition = response.headers['content-disposition']
    const fileName = contentDisposition
      ? contentDisposition.split('filename=')[1].replace(/"/g, '')
      : 'kaapana_datasets_download.zip'

    link.setAttribute('download', fileName)
    document.body.appendChild(link)
    link.click()

    URL.revokeObjectURL(link.href)
    document.body.removeChild(link)
  } catch (error: unknown) {
    // With responseType 'blob' the error body is a Blob too.
    // Parse it so the caller can read the error message.
    const response = isAxiosError(error) ? error.response : undefined
    if (response?.data instanceof Blob) {
      try {
        response.data = JSON.parse(await response.data.text())
      } catch {
        // No valid JSON.
      }
    }
    throw error
  }
}

export {
  updateTags,
  loadPatients,
  loadSeriesData,
  createDataset,
  updateDataset,
  deleteDataset,
  loadDatasets,
  loadDatasetByName,
  loadDashboard,
  loadDicomTagMapping,
  loadFieldNames,
  loadValues,
  loadSearchFields,
  getAggregatedSeriesNum,
  downloadDatasets,
}
