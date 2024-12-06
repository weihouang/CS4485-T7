import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:5000',  // Make sure this matches your FastAPI server
  headers: {
    'Content-Type': 'application/json',
  },
});

export default apiClient;
