/**
 * Configuration de l'application
 */

export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  env: import.meta.env.VITE_ENV || 'development',
  isDevelopment: import.meta.env.VITE_ENV === 'development',
  isProduction: import.meta.env.VITE_ENV === 'production',
}

export default config

