import Vue from 'vue'
import AuthService from '@/common/auth.service'
import httpClient from './httpClient'

  const helmApiPost = (subUrl: any, payload: any, timeout: any = 10000) => {
    return new Promise((resolve, reject) => {
      httpClient.defaults.timeout = timeout
      httpClient.post('/kube-helm-api' + subUrl, payload).then((response: any) => {
        console.log(response)
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.response.data)
        reject(error)
      })
    })
  }

  const helmApiGet = (subUrl: any, params: any, timeout: any = 10000) => {
    return new Promise((resolve, reject) => {
      httpClient.defaults.timeout = timeout
      httpClient.get('/kube-helm-api' + subUrl, { params }).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.response.data)
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
      })
    })
  }

  const getExternalWebpages = () => {
    return new Promise((resolve, reject) => {


      httpClient.get('/jsons/defaultExternalWebpages.json').then((response: { data: any }) => {

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
        
        
        //// The following section checks, if the routes listed in the config file externalWebpages.json is also available, enabled and correctly configured in traefik.
        //// I.E. if there is a service in traefik that routes to the configured endpoint
        httpClient.get('/kaapana-backend/get-traefik-routes').then((response: { data: {} }) => {
          trainingJson = response.data

          for (const key1 in externalWebpages) {
            if (externalWebpages.hasOwnProperty(key1)) {
              for (const key2 in externalWebpages[key1].subSections) {
                if (externalWebpages[key1].subSections.hasOwnProperty(key2)) {
                  if (!checkUrl(trainingJson, externalWebpages[key1].subSections[key2].endpoint)) {
                    delete externalWebpages[key1].subSections[key2]
                  }
                }
              }
            }
          }
        }).then(() => {
          
          //// Get a list of the available dashboards in opensearch and add them as subsections to the meta section.
          let osDashboardsUrl = '/kaapana-backend/get-os-dashboards'
          httpClient.get(osDashboardsUrl)
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
  }
  const checkUrl = (trainingJson: any, endpoint: any) => {
    let availableRoute = false
    for (const routes in trainingJson) {
      if (trainingJson[routes]['status'] == 'enabled') {
        if (trainingJson[routes]['rule'].slice(12, -2) == endpoint) {
          availableRoute = true
        }
      }
    }
    return availableRoute
  }

  const federatedClientApiPost = (subUrl: any, payload: any = null, params: any=null) => {
    return new Promise((resolve, reject) => {
      httpClient.post('/kaapana-backend/client' + subUrl, payload, { params: params}).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.response.data)
        reject(error)
      })
    })
  }

  const federatedClientApiGet = (subUrl: any, params: any = null) => {
    return new Promise((resolve, reject) => {
      httpClient.get('/kaapana-backend/client' + subUrl, { params }).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.response.data)
        reject(error)
      })
    })
  }

  const federatedClientApiPut = (subUrl: any, payload: any=null, params: any=null) => {
    return new Promise((resolve, reject) => {
      httpClient.put('/kaapana-backend/client' + subUrl,  payload, { params: params }).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.response.data)
        reject(error)
      })
    })
  }

  const federatedClientApiDelete = (subUrl: any, params: any = null) => {
    return new Promise((resolve, reject) => {
      httpClient.delete('/kaapana-backend/client' + subUrl, { params: params} ).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.response.data)
        reject(error)
      })
    })
  }

  const federatedRemoteApiPut = (subUrl: any, payload: any = null,  params: any=null) => {
    return new Promise((resolve, reject) => {
      AuthService.getFederatedHeaders().then((response: any) =>  {
        httpClient.put('/kaapana-backend/remote' + subUrl, payload, { params: params, headers: response}).then((response: any) => {
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
  }

  const federatedRemoteApiPost = (subUrl: any, payload: any=null, params: any=null) => {
    return new Promise((resolve, reject) => {
      AuthService.getFederatedHeaders().then((response: any) =>  {
        httpClient.post('/kaapana-backend/remote' + subUrl, payload, {params: params, headers: response}).then((response: any) => {
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
  }

  const federatedRemoteApiGet = (subUrl: any, params: any = null) => {
    return new Promise((resolve, reject) => {
      AuthService.getFederatedHeaders().then((response: any) =>  {
        httpClient.get('/kaapana-backend/remote' + subUrl, { params , headers: response}).then((response: any) => {
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
  }
  const federatedRemoteApiDelete = (subUrl: any, params: any = null) => {
    return new Promise((resolve, reject) => {
      AuthService.getFederatedHeaders().then((response: any) =>  {
        httpClient.delete('/kaapana-backend/remote' + subUrl, { params , headers: response}).then((response: any) => {
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

  const kaapanaApiPut = (subUrl: any, payload: any=null, params: any=null) => {
    return new Promise((resolve, reject) => {
      httpClient.put('/kaapana-backend' + subUrl,  payload, { params: params }).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.response.data)
        reject(error)
      })
    })
  }

  const kaapanaApiDelete = (subUrl: any, params: any = null) => {
    return new Promise((resolve, reject) => {
      httpClient.delete('/kaapana-backend' + subUrl, { params: params} ).then((response: any) => {
        resolve(response)
      }).catch((error: any) => {
        console.log('Failed: ' + error.response.data)
        reject(error)
      })
    })
  }

  const syncRemoteInstances = () => {
        return federatedClientApiGet("/check-for-remote-updates")
        .then((response) => {
          Vue.notify({
            type: 'success',
            title: 'Successfully checked for remote updates',
            // text: 
          })
          return true
        })
        .catch((err) => {
          console.log(err);
          // return false
        });
    }
  const kaapanaApiService = {
    helmApiPost,
    helmApiGet,
    getPolicyData,
    getExternalWebpages,
    checkUrl,
    federatedClientApiPost,
    federatedClientApiGet,
    federatedClientApiPut,
    federatedClientApiDelete,
    federatedRemoteApiPut,
    federatedRemoteApiPost,
    federatedRemoteApiGet,
    federatedRemoteApiDelete,
    kaapanaApiGet,
    kaapanaApiPut,
    kaapanaApiDelete,
    syncRemoteInstances
  }

export default kaapanaApiService;
