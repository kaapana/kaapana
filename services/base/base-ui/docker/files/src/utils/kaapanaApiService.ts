import { notify } from '@kyvg/vue3-notification'
import { httpClient } from './httpClient'

  const helmApiPost = (subUrl: any, payload: any, timeout: any = 10000) => {
    return new Promise((resolve, reject) => {
      httpClient.post('/kube-helm-api' + subUrl, payload, { timeout }).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error?.response?.data)
        reject(error)
      })
    })
  }

  const helmApiGet = (subUrl: any, params: any, timeout: any = 10000) => {
    return new Promise((resolve, reject) => {
      httpClient.get('/kube-helm-api' + subUrl, { params, timeout }).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error?.response?.data)
        reject(error)
      })
    })
  }

  const getPolicyData = () => {
    return new Promise((resolve, reject) => {
      httpClient.get('/kaapana-backend/open-policy-data').then((response: { data: any }) => {
        const policyData = response.data
        resolve(policyData)
      }).catch((error:any) => {
        console.log('Something went wrong with open policy agent ', error)
        reject(error)
      })
    })
  }

  const federatedClientApiPost = (subUrl: any, payload: any = null, params: any=null) => {
    return new Promise((resolve, reject) => {
      httpClient.post('/kaapana-backend/client' + subUrl, payload, { params: params}).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed:', error.response ? error.response.data : error.message)
        reject(error)
      })
    })
  }

  const federatedClientApiGet = (subUrl: any, params: any = null) => {
    return new Promise((resolve, reject) => {
      httpClient.get('/kaapana-backend/client' + subUrl, { params }).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed:', error.response ? error.response.data : error.message)
        reject(error)
      })
    })
  }

  const federatedClientApiPut = (subUrl: any, payload: any=null, params: any=null) => {
    return new Promise((resolve, reject) => {
      httpClient.put('/kaapana-backend/client' + subUrl,  payload, { params: params }).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed:', error.response ? error.response.data : error.message)
        reject(error)
      })
    })
  }

  const federatedClientApiDelete = (subUrl: any, params: any = null) => {
    return new Promise((resolve, reject) => {
      httpClient.delete('/kaapana-backend/client' + subUrl, { params: params} ).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed:', error.response ? error.response.data : error.message)
        reject(error)
      })
    })
  }

  const kaapanaApiGet = (subUrl: any, params: any = null) => {
    return new Promise((resolve, reject) => {
      httpClient.get('/kaapana-backend' + subUrl, { params: params }).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed:', error.response ? error.response.data : error.message);
        reject(error)
      })
    })
  }

  const syncRemoteInstances = () => {
        return federatedClientApiGet("/check-for-remote-updates")
        .then((response) => {
          notify({
            type: 'success',
            title: 'Successfully checked for remote updates',
          })
          return true
        })
    }
  const kaapanaApiService = {
    helmApiPost,
    helmApiGet,
    getPolicyData,
    federatedClientApiPost,
    federatedClientApiGet,
    federatedClientApiPut,
    federatedClientApiDelete,
    kaapanaApiGet,
    syncRemoteInstances
  }

export default kaapanaApiService;
