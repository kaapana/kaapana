import Vue from 'vue'
import request from '@/request.ts'

const AuthService = {
  getToken() {
    return new Promise((resolve, reject) => {
      let oauthUrl = ''
      if (Vue.config.productionTip === true) {
        oauthUrl = '/oauth/token'
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
    location.href = '/oauth/logout?redirect=/'
    //location.href = '/oauth/logout' // without redirect since redirect lead often to the error page and people had to renter the url
  },
}
export default AuthService
