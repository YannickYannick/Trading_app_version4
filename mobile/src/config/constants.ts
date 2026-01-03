import { Platform } from 'react-native'

// URL de base de l'API
// Android Emulator utilise 10.0.2.2 pour localhost
// iOS Simulator utilise localhost
// Device physique nécessite l'IP locale de vore machine
const DEV_API_URL = Platform.select({
  android: 'http://192.168.1.171:8000/api', // IP locale détectée (pour Device physique ET Emulateur)
  ios: 'http://192.168.1.171:8000/api',
  default: 'http://192.168.1.171:8000/api',
})

export const API_URL = __DEV__ ? DEV_API_URL : 'https://votre-api-prod.com/api'

export const config = {
  apiBaseUrl: API_URL,
  timeout: 30000,
}
