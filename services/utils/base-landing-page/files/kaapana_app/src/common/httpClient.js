import axios from 'axios';
import store from '../store/index'; 

const httpClient = axios.create({
  headers: {
  },
  timeout: 10000
});

const httpClientWithoutTimeout = axios.create({
  headers: {},
  timeout: 0
});

export default httpClient;
export { httpClientWithoutTimeout };
