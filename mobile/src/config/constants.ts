import { Platform } from 'react-native';

// URL de base de l'API
// On utilise l'URL de production car elle est accessible depuis le téléphone via internet/4G/Wifi
// contrairement au serveur local qui pose des problèmes de réseau (10.0.2.2 vs IP locale vs localhost)
// En dev, on peut surcharger si nécessaire, mais pour l'instant on force la prod comme sur le build qui marche.

const PROD_API_URL = 'https://le-baff.com/api';
const LOCAL_API_URL = 'http://192.168.1.171:8000/api'; // Fallback local au cas où

export const API_BASE_URL = __DEV__
  ? PROD_API_URL // Même en dev, on utilise la prod pour l'instant pour garantir la connexion
  : PROD_API_URL;

export const AUTH_TOKEN_KEY = 'auth_token';
export const REFRESH_TOKEN_KEY = 'refresh_token';

export const config = {
  apiBaseUrl: API_BASE_URL,
  timeout: 30000,
};
