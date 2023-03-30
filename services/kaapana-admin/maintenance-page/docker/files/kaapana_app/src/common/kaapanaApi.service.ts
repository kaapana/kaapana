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

  getExternalWebpages() {
    return new Promise((resolve, reject) => {


      request.get('/jsons/defaultExternalWebpages.json').then((response: { data: any }) => {

        const externalWebpages = response.data

        let trainingJson = {}


        for (const key1 in externalWebpages) {
          if (externalWebpages.hasOwnProperty(key1)) {
            for (const key2 in externalWebpages[key1].subSections) {
              if (externalWebpages[key1].subSections.hasOwnProperty(key2)) {
                externalWebpages[key1].subSections[key2].linkTo =
                  location.protocol + '//' + location.host + externalWebpages[key1].subSections[key2].linkTo
              }
            }
          }
        }

        let traefikUrl = ''
        if (Vue.config.productionTip === true) {
          traefikUrl = '/traefik/api/http/routers'
        } else {
          traefikUrl = '/jsons/testingTraefikResponse.json'
        }

        request.get(traefikUrl).then((response: { data: {} }) => {
          trainingJson = response.data

          for (const key1 in externalWebpages) {
            if (externalWebpages.hasOwnProperty(key1)) {
              for (const key2 in externalWebpages[key1].subSections) {
                if (externalWebpages[key1].subSections.hasOwnProperty(key2)) {
                  if (!this.checkUrl(trainingJson, externalWebpages[key1].subSections[key2].endpoint)) {
                    delete externalWebpages[key1].subSections[key2]
                  }
                }
              }
            }
          }
        }).then(() => {

          let osDashboardsUrl = '/flow/kaapana/api/get-os-dashboards'
          request.get(osDashboardsUrl)
            .then((response: { data: any }) => {
              var dashboards = response.data['dashboards']
              const osDashboardsSubsections: { [k: string]: any } = {};
              dashboards.forEach((title: string, index: any) => {
                osDashboardsSubsections['osdashboard' + String(index)] =
                {
                  label: title,
                  linkTo: location.protocol + '//' + location.host + '/meta/app/dashboards#?title=' + title + '&embed=true&_g=()',
                }
              });

              externalWebpages.meta.subSections = Object.assign(externalWebpages.meta.subSections, osDashboardsSubsections) // might not work in all browsers

              resolve(externalWebpages)

            }).catch((err: any) => {
              console.log('Something went wrong with OpenSearch Dashboards', err)
              resolve(externalWebpages)
            })
        }).catch((error: any) => {
          console.log('Something went wrong with traefik', error)
          resolve(externalWebpages)
          // reject(error)
        })
      }).catch((error: any) => {
        console.log('Something went wrong loading the default external wepages', error)
        // reject(error)
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
