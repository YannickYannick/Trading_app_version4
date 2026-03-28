import { Platform } from 'react-native';

// URL de base de l'API
// IMPORTANT: Pour le développement mobile, on utilise l'IP locale du PC
// car le téléphone ne peut pas accéder à "localhost" ou "127.0.0.1"
// L'IP doit être celle de votre PC sur le réseau local (trouvée avec ipconfig)

const PROD_API_URL = 'https://le-baff.com/api';
const LOCAL_API_URL = 'http://192.168.236.173:8000/api'; // IP locale mise à jour

export const API_BASE_URL = __DEV__
  ? LOCAL_API_URL // En dev, on utilise le serveur local pour éviter les problèmes SSL/CORS
  : PROD_API_URL;

export const AUTH_TOKEN_KEY = 'auth_token';
export const REFRESH_TOKEN_KEY = 'refresh_token';

export const config = {
  apiBaseUrl: API_BASE_URL,
  timeout: 30000,
};
