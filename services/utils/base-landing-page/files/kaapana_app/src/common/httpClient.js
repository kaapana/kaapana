import axios from 'axios';
import store from '../store/index'; 

const httpClient = axios.create({
  headers: {
  },
  timeout: 10000
});

export default httpClient;
