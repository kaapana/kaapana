import Vue from 'vue'
import httpClient from './httpClient'

const AuthService = {
  getToken() {
    return new Promise((resolve, reject) => {
      let oauthUrl = ''
      if (Vue.config.productionTip === true) {
        oauthUrl = '/oauth2/userinfo'
      } else {
        oauthUrl = '/jsons/testingAuthenticationToken.json'
      }
      httpClient.get(oauthUrl).then((response: any) =>  {
        resolve(response.data)
      }).catch((error: any) => {
        console.log('not token there', error)
        reject(error)
      })

    })
  },
  logout() {
    location.href = '/kaapana-backend/oidc-logout'
  },
  getFederatedHeaders() {
    return new Promise((resolve, reject) => {
      httpClient.get('/kaapana-backend/client/kaapana-instance').then((response: any) =>  {
        resolve({
          FederatedAuthorization: response.data['token']
        })
      }).catch((error: any) => {
        // console.log('not token there', error)
        // reject(error)
      })

    })
  }
}
export default AuthService
