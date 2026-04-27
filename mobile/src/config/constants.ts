import { Platform } from 'react-native';
import Constants from 'expo-constants';
import * as Device from 'expo-device';

// URL API en production (Railway). Doit pointer vers la racine API "/api".
const PROD_API_URL = 'https://trading-production-edd7.up.railway.app/api';

/**
 * IP LAN de ton PC (voir `ipconfig`) pour un téléphone Android physique.
 * Sur émulateur, l’hôte est 10.0.2.2 (voir isAndroidEmulator).
 */
const DEV_API_HOST_LAN = '192.168.1.171';

/** Forcer l’URL émulateur si la détection échoue : EXPO_PUBLIC_FORCE_EMULATOR_API=1 */
const FORCE_EMULATOR_API =
  process.env.EXPO_PUBLIC_FORCE_EMULATOR_API === '1' ||
  process.env.EXPO_PUBLIC_FORCE_EMULATOR_API === 'true';

/**
 * Hôte API depuis l’émulateur Android → la machine hôte.
 * Défaut `10.0.2.2` : alias standard vers le loopback du PC (Django `runserver` sur 127.0.0.1:8000).
 * Si tu préfères l’IP LAN : EXPO_PUBLIC_ANDROID_EMU_HOST=192.168.x.x et lance
 * `python manage.py runserver 0.0.0.0:8000` pour que le port soit joignable sur cette IP.
 */
const ANDROID_EMU_API_HOST = (
  process.env.EXPO_PUBLIC_ANDROID_EMU_HOST ?? '10.0.2.2'
).trim();

/**
 * Les AVD « Pixel 7 » ont souvent un Model ressemblant à un vrai appareil alors que
 * Platform.constants.Fingerprint contient sdk_gphone / gphone. Expo Go peut aussi
 * mal remplir expo-device → on lit d’abord les constantes React Native.
 */
function isAndroidEmulator(): boolean {
  if (Platform.OS !== 'android') return false;

  const ac = Platform.constants as {
    Fingerprint?: string;
    Model?: string;
    Brand?: string;
    Manufacturer?: string;
  };

  const fp = (
    ac.Fingerprint ??
    Device.osBuildFingerprint ??
    ''
  ).toLowerCase();

  const model = (
    ac.Model ??
    Device.modelName ??
    ''
  ).toLowerCase();

  const emuSubstrings = [
    'sdk_gphone',
    'gphone64',
    'gphone',
    'emu64',
    'emulator',
    'generic',
    'ranchu',
    'goldfish',
    'vbox',
    'generic_x86',
    'google_sdk',
  ];

  for (const s of emuSubstrings) {
    if (fp.includes(s) || model.includes(s)) return true;
  }

  return false;
}

function normalizeApiBaseUrl(url: string): string {
  const trimmed = url.replace(/\/$/, '');
  return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`;
}

function resolveDevApiBaseUrl(): string {
  const useProdInDev =
    process.env.EXPO_PUBLIC_USE_PROD_API_IN_DEV === '1' ||
    process.env.EXPO_PUBLIC_USE_PROD_API_IN_DEV === 'true';
  if (useProdInDev) {
    return PROD_API_URL;
  }

  const override = process.env.EXPO_PUBLIC_DEV_API_URL;
  if (override && override.trim().length > 0) {
    return normalizeApiBaseUrl(override.trim());
  }

  if (Platform.OS === 'android') {
    if (FORCE_EMULATOR_API || isAndroidEmulator()) {
      return `http://${ANDROID_EMU_API_HOST}:8000/api`;
    }
    return `http://${DEV_API_HOST_LAN}:8000/api`;
  }

  if (Platform.OS === 'ios' && Constants.isDevice === false) {
    return 'http://127.0.0.1:8000/api';
  }

  return `http://${DEV_API_HOST_LAN}:8000/api`;
}

export const API_BASE_URL = __DEV__ ? resolveDevApiBaseUrl() : PROD_API_URL;

if (__DEV__) {
  console.log('[API] DEV base URL →', API_BASE_URL)
  if (Platform.OS === 'android' && (FORCE_EMULATOR_API || isAndroidEmulator())) {
    if (ANDROID_EMU_API_HOST === '127.0.0.1') {
      console.log(
        '[API] Émulateur + 127.0.0.1 : lance `npm run android:reverse` (8081 + 8000) puis Django sur le PC.',
      )
    } else if (ANDROID_EMU_API_HOST === '10.0.2.2') {
      console.log(
        '[API] Émulateur : Django sur le PC doit écouter sur le port 8000 (ex. `python manage.py runserver`). Hôte 10.0.2.2 → PC.',
      )
    } else {
      console.log(
        '[API] Émulateur (IP LAN) : `python manage.py runserver 0.0.0.0:8000`, pare-feu port 8000. Prod en dev : EXPO_PUBLIC_USE_PROD_API_IN_DEV=1',
      )
    }
  }
}

export const AUTH_TOKEN_KEY = 'auth_token';
export const REFRESH_TOKEN_KEY = 'refresh_token';

export const config = {
  apiBaseUrl: API_BASE_URL,
  timeout: 30000,
};
