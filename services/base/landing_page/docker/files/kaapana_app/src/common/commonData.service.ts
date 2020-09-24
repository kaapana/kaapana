import request from '@/request.ts'

const CommonDataService = {
  getCommonData() {
    return new Promise((resolve, reject) => {

      request.get('/jsons/commonData.json').then((response) => {
        resolve(response.data)
      }).catch(error => {
        console.log('Something went wrong loading the common Data', error)
        // reject(error)
      })
    })
  },
  getLaunchApplication() {
    return new Promise((resolve, reject) => {

      request.get('/jsons/launchApplication.json').then((response) => {
        resolve(response.data)
      }).catch(error => {
        console.log('Something went wrong loading the launch Application Data', error)
        // reject(error)
      })
    })
  },
}

export default CommonDataService
