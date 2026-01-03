import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../config/constants';

// Create axios instance
const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor
client.interceptors.request.use(
  async (config) => {
    try {
      const token = await SecureStore.getItemAsync(AUTH_TOKEN_KEY);
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('Error retrieving token', error);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor (basic error handling for now)
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    // TODO: Implement refresh token logic here
    if (error.response && error.response.status === 401) {
      // Handle unauthorized (e.g., logout or refresh)
      console.log('Unauthorized access - redirect to login or refresh token');
    }
    return Promise.reject(error);
  }
);

export default client;
