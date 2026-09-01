import { httpClient } from '@kaapana/base-ui'

const CommonDataService = {
  getCommonData() {
    return new Promise((resolve, reject) => {

      httpClient.get('/jsons/commonData.json').then((response: any) => {
        resolve(response.data)
      }).catch((error: any) => {
        reject(error)
      })
    })
  }
}

export default CommonDataService
