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
        console.log('Failed: ' + error.response.data)
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
        console.log('Failed: ' + error.response.data)
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
}

export default kaapanaApiService
