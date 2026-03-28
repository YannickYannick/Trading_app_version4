import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../config/constants';

// Create axios instance
const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 second timeout
});

// Log the API configuration on startup
console.log('📡 API Client initialized with baseURL:', API_BASE_URL);

// Add request interceptor
client.interceptors.request.use(
  async (config) => {
    try {
      const token = await SecureStore.getItemAsync(AUTH_TOKEN_KEY);
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      console.log(`🔵 API Request: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
    } catch (error) {
      console.error('❌ Error retrieving token', error);
    }
    return config;
  },
  (error) => {
    console.error('❌ Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor (basic error handling for now)
client.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.config.method?.toUpperCase()} ${response.config.url} - Status: ${response.status}`);
    return response;
  },
  async (error) => {
    // Log detailed error information
    if (error.response) {
      // Server responded with error status
      console.error(`❌ API Error Response: ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
        status: error.response.status,
        data: error.response.data,
      });
    } else if (error.request) {
      // Request was made but no response received
      console.error(`❌ API Network Error: ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
        message: error.message,
        baseURL: error.config?.baseURL,
      });
    } else {
      // Something else happened
      console.error('❌ API Error:', error.message);
    }

    // TODO: Implement refresh token logic here
    if (error.response && error.response.status === 401) {
      // Handle unauthorized (e.g., logout or refresh)
      console.log('⚠️ Unauthorized access - redirect to login or refresh token');
    }
    return Promise.reject(error);
  }
);

export default client;
