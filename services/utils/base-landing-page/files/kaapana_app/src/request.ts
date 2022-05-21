import Vue from 'vue'
import Axios from 'axios'

const axiosInstance = Axios.create({
  baseURL: location.protocol + '//' + location.host,
  timeout: 5000,
})

export default axiosInstance
