import { notify } from '@kyvg/vue3-notification'
import { httpClient } from '@kaapana/base-ui'

const KAAPANA_BACKEND_ENDPOINT = import.meta.env.VITE_KAAPANA_BACKEND_ENDPOINT

const loadDatasets = async (skipIdentifiers = true) => {
  try {
    const datasets = await httpClient.get(KAAPANA_BACKEND_ENDPOINT + 'client/datasets', {
      params: skipIdentifiers ? { skip_identifiers: true } : {},
    })
    return datasets.data
  } catch (error: any) {
    notify({
      title: 'Error',
      text:
        error.response && error.response.data && error.response.data.detail
          ? error.response.data.detail
          : error,
      type: 'error',
    })
    throw error
  }
}

export { loadDatasets }
