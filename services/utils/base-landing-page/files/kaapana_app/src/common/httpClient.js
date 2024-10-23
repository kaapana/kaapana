import axios from 'axios';
import store from '../store/index'; 

const httpClient = axios.create({
  headers: {
  },
  timeout: 10000
});

httpClient.interceptors.request.use((config) => {
  const selectedProject = store.getters.selectedProject
  if (selectedProject) {
    config.headers['Project'] = JSON.stringify(selectedProject); 
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export default httpClient;
