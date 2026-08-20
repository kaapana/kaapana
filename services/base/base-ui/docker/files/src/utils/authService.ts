import { httpClient } from './httpClient'

export interface UserinfoJwt {
  preferredUsername: string
  groups: string[]
  user: string
}

const AuthService = {
  getToken(): Promise<UserinfoJwt> {
    return new Promise((resolve, reject) => {
      // In dev mode the auth proxy is absent; a static token file stands in.
      // The PROD switch stays unresolved in the built library (see
      // vite.config.ts) so the consuming view's own build decides.
      const oauthUrl = import.meta.env.PROD
        ? '/oauth2/userinfo'
        : '/jsons/testingAuthenticationToken.json'
      httpClient
        .get(oauthUrl)
        .then((response) => {
          resolve(response.data)
        })
        .catch((error) => {
          console.log('not token there', error)
          reject(error)
        })
    })
  },
  logout() {
    location.href = '/kaapana-backend/oidc-logout'
  },
}
export default AuthService
