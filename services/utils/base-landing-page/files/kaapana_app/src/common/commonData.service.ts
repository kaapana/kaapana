import httpClient from './httpClient'

const CommonDataService = {
  getCommonData() {
    return new Promise((resolve, reject) => {

      httpClient.get('/jsons/commonData.json').then((response: any) => {
        resolve(response.data)
      }).catch((error: any) => {
        console.log('Something went wrong loading the common Data', error)
        // reject(error)
      })
    })
  }
}

export default CommonDataService
