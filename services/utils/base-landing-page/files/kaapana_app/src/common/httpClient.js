import axios from 'axios';

const httpClient = axios.create({
  headers: {
    // "Content-Type": "application/json",
    "Project": localStorage.getItem("selectedProject")
  },
  timeout: 10000
});

export default httpClient;
