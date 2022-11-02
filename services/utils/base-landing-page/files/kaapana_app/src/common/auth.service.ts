import Vue from 'vue'
import request from '@/request.ts'

const AuthService = {
  getToken() {
    return new Promise((resolve, reject) => {
      let oauthUrl = ''
      if (Vue.config.productionTip === true) {
        oauthUrl = '/oauth2/userinfo'
      } else {
        oauthUrl = '/jsons/testingAuthenticationToken.json'
      }
      request.get(oauthUrl).then((response: any) =>  {
        resolve(response.data)
      }).catch((error: any) => {
        console.log('not token there', error)
        reject(error)
      })

    })
  },
  logout() {
    location.href = '/oauth2/sign_out?rd=/auth/realms/kaapana/protocol/openid-connect/logout'
    //location.href = '/oauth/logout' // without redirect since redirect lead often to the error page and people had to renter the url
  },
  getFederatedHeaders() {
    return new Promise((resolve, reject) => {
      request.get('/kaapana-backend/client/client-kaapana-instance').then((response: any) =>  {
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
