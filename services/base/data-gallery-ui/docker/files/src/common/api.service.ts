import { notify } from '@kyvg/vue3-notification'
import { httpClient, httpClientWithoutTimeout, useAuthStore } from '@kaapana/base-ui'
import { apiErrorText } from '@/utils/errors'
import type { Dataset } from '@/types'

const KAAPANA_BACKEND_ENDPOINT = import.meta.env.VITE_KAAPANA_BACKEND_ENDPOINT

// Every failure is reported as "what failed" plus, when the backend supplied
// one, the actionable detail — never the bare Error, which used to be
// interpolated straight into the notification as "[object Object]" whenever the
// response carried no `detail` (design guidelines, "Errors").
const notifyError = (error: any, title: string, fallback: string) => {
  notify({
    title,
    text: apiErrorText(error, fallback),
    type: 'error',
  })
}

const updateDataset = async (body: any) => {
  return await httpClient.put(KAAPANA_BACKEND_ENDPOINT + 'client/dataset', body)
}

const createDataset = async (body: any) => {
  return await httpClient.post(KAAPANA_BACKEND_ENDPOINT + 'client/dataset', body)
}

const deleteDataset = async (datasetName: string) => {
  try {
    const res = await httpClient.delete(
      KAAPANA_BACKEND_ENDPOINT + `client/dataset?name=${encodeURIComponent(datasetName)}`,
    )
    return res.data['ok']
  } catch (error: any) {
    notifyError(error, 'Dataset not deleted', 'The dataset could not be deleted.')
    throw error
  }
}

const loadDatasetByName = async (datasetName: string, access_level = 'project') => {
  try {
    const dataset = (
      await httpClient.get(
        KAAPANA_BACKEND_ENDPOINT +
          `client/dataset?name=${encodeURIComponent(datasetName)}&access_level=${encodeURIComponent(access_level)}`,
      )
    ).data
    return dataset
  } catch (error: any) {
    notifyError(error, 'Dataset not loaded', 'The dataset could not be loaded; the search is not scoped to it.')
    throw error
  }
}

const loadDatasets = async (skipIdentifiers = true): Promise<Dataset[]> => {
  try {
    const datasets = await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'client/datasets', {
      params: skipIdentifiers ? { skip_identifiers: true } : {},
    })
    return datasets.data
  } catch (error: any) {
    notifyError(error, 'Datasets not loaded', 'The list of datasets could not be loaded.')
    throw error
  }
}

const loadSeriesData = async (seriesInstanceUID: string) => {
  try {
    const response = await httpClient.get(
      KAAPANA_BACKEND_ENDPOINT + `dataset/series/${seriesInstanceUID}`,
    )
    return response.data
  } catch (error: any) {
    notifyError(error, 'Series metadata not loaded', 'The metadata for this series could not be loaded.')
    throw error
  }
}

const loadPatients = async (data: any) => {
  try {
    const res = await httpClient.post(KAAPANA_BACKEND_ENDPOINT + 'dataset/series', data)
    return res.data
  } catch (error: any) {
    notifyError(error, 'Series not loaded', 'The series matching this search could not be loaded.')
    throw error
  }
}

const getAggregatedSeriesNum = async (data: any) => {
  try {
    const res = await httpClient.post(
      KAAPANA_BACKEND_ENDPOINT + 'dataset/aggregatedSeriesNum',
      data,
    )
    return res.data
  } catch (error: any) {
    notifyError(error, 'Series count unavailable', 'The number of matching series could not be determined, so paging may be wrong.')
    throw error
  }
}

const loadFieldNames = async () => {
  try {
    return await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'dataset/field_names')
  } catch (error: any) {
    notifyError(error, 'Filter fields not loaded', 'The fields available for filtering could not be loaded.')
    throw error
  }
}

const loadValues = async (key: string, query: any = {}) => {
  try {
    return await httpClient.post(
      KAAPANA_BACKEND_ENDPOINT + `dataset/query_values/${encodeURIComponent(key)}`,
      query,
    )
  } catch (error: any) {
    notifyError(error, 'Filter values not loaded', 'The selectable values for this filter could not be loaded.')
    throw error
  }
}

const loadSearchFields = async () => {
  try {
    const response = await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'dataset/search_fields')
    return response.data
  } catch (error: any) {
    notifyError(error, 'Search fields not loaded', 'The searchable fields could not be loaded, so free-text search is unavailable.')
    throw error
  }
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
  } catch (error: any) {
    if (error.response && error.response.data) {
      // The error body is also a Blob (responseType 'blob'), so read it first.
      const reader = new FileReader()
      reader.onload = function () {
        let errorText = 'The download could not be completed.'
        try {
          const detail = JSON.parse(reader.result as string)?.detail
          if (typeof detail === 'string' && detail.trim() !== '') {
            errorText = `The download could not be completed. ${detail.trim()}`
          }
        } catch {
          // The body was not the expected JSON problem report; the sentence
          // above is still the useful thing to show, so keep it.
        }
        notify({
          title: 'Download failed',
          text: errorText,
          type: 'error',
        })
      }
      reader.readAsText(error.response.data)
    } else {
      console.error('Unexpected error:', error)
    }

    throw error
  }
}

const fetchProjects = async () => {
  const currentUser = useAuthStore().currentUser
  try {
    if (currentUser.roles.includes('admin')) {
      return (await httpClient.get('/aii/projects')).data
    } else {
      return (await httpClient.get('/aii/users/' + currentUser.id + '/projects')).data
    }
  } catch (error: any) {
    notifyError(error, 'Projects not loaded', 'Your projects could not be loaded.')
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
  fetchProjects,
  downloadDatasets,
}
