import Vue from 'vue'
import request from '@/request'
import AuthService from '@/common/auth.service'

const kaapanaApiService = {

  helmApiPost(subUrl: any, payload: any, timeout: any = 10000) {
    return new Promise((resolve, reject) => {
      request.defaults.timeout = timeout
      request.post('/kube-helm-api' + subUrl, payload).then((response: any) => {
        console.log(response)
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.data)
        reject(error)
      })
    })
  },

  helmApiGet(subUrl: any, params: any, timeout: any = 10000) {
    return new Promise((resolve, reject) => {
      request.defaults.timeout = timeout
      request.get('/kube-helm-api' + subUrl, { params }).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.data)
        reject(error)
      })
    })
  },

  checkUrl(trainingJson: any, endpoint: any) {
    let availableRoute = false
    for (const routes in trainingJson) {
      if (trainingJson[routes]['status'] == 'enabled') {
        if (trainingJson[routes]['rule'].slice(12, -2) == endpoint) {
          availableRoute = true
        }
      }
    }
    return availableRoute
  },

  federatedClientApiPost(subUrl: any, payload: any = null, params: any=null) {
    return new Promise((resolve, reject) => {
      request.post('/kaapana-backend/client' + subUrl, payload, { params: params}).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.response.data)
        reject(error)
      })
    })
  },

  federatedClientApiGet(subUrl: any, params: any = null) {
    return new Promise((resolve, reject) => {
      request.get('/kaapana-backend/client' + subUrl, { params }).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.response.data)
        reject(error)
      })
    })
  },

  federatedClientApiPut(subUrl: any, payload: any=null, params: any=null) {
    return new Promise((resolve, reject) => {
      request.put('/kaapana-backend/client' + subUrl,  payload, { params: params }).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.response.data)
        reject(error)
      })
    })
  },

  federatedClientApiDelete(subUrl: any, params: any = null) {
    return new Promise((resolve, reject) => {
      request.delete('/kaapana-backend/client' + subUrl, { params: params} ).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.response.data)
        reject(error)
      })
    })
  },

  federatedRemoteApiPut(subUrl: any, payload: any = null,  params: any=null) {
    return new Promise((resolve, reject) => {
      AuthService.getFederatedHeaders().then((response: any) =>  {
        request.put('/kaapana-backend/remote' + subUrl, payload, { params: params, headers: response}).then((response: any) => {
          resolve(response)
        }).catch((error: any) => {
          console.log('Failed: ' + error.response.data)
          reject(error)
        })
      }).catch((error: any) => {
        console.log(error);
        reject(error)
      });
    })
  },

  federatedRemoteApiPost(subUrl: any, payload: any=null, params: any=null) {
    return new Promise((resolve, reject) => {
      AuthService.getFederatedHeaders().then((response: any) =>  {
        request.post('/kaapana-backend/remote' + subUrl, payload, {params: params, headers: response}).then((response: any) => {
          resolve(response)
        }).catch((error: any) => {
          console.log('Failed: ' + error.response.data)
          reject(error)
        })
      }).catch((error: any) => {
        console.log(error);
        reject(error)
      });
    })
  },

  federatedRemoteApiGet(subUrl: any, params: any = null) {
    return new Promise((resolve, reject) => {
      AuthService.getFederatedHeaders().then((response: any) =>  {
        request.get('/kaapana-backend/remote' + subUrl, { params , headers: response}).then((response: any) => {
          resolve(response)
        }).catch((error: any) => {
          console.log('Failed: ' + error.response.data)
          reject(error)
        })
      }).catch((error: any) => {
        console.log(error);
        reject(error)
      });
    })
  },
  federatedRemoteApiDelete(subUrl: any, params: any = null) {
    return new Promise((resolve, reject) => {
      AuthService.getFederatedHeaders().then((response: any) =>  {
        request.delete('/kaapana-backend/remote' + subUrl, { params , headers: response}).then((response: any) => {
          resolve(response)
        }).catch((error: any) => {
          console.log('Failed: ' + error.response.data)
          reject(error)
        })
      }).catch((error: any) => {
        console.log(error);
        reject(error)
      });
    })
  },
  kaapanaApiGet(subUrl: any, params: any = null) {
    return new Promise((resolve, reject) => {
      request.get('/flow/kaapana/api/' + subUrl, { params }).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.data)
        reject(error)
      })
    })
  }
}

export default kaapanaApiService
