import AsyncStorage from '@react-native-async-storage/async-storage'
import * as SecureStore from 'expo-secure-store'
import { Platform } from 'react-native'
import type { StorageAdapter } from '@trading-app/shared'

/**
 * Adaptateur de stockage pour Mobile
 * Utilise SecureStore pour les tokens et clés sensibles
 * Utilise AsyncStorage pour les données non sensibles
 */
export class MobileStorageAdapter implements StorageAdapter {
    private secureKeys = ['access_token', 'refresh_token']

    async getItem(key: string): Promise<string | null> {
        if (this.secureKeys.includes(key)) {
            if (Platform.OS === 'web') return AsyncStorage.getItem(key) // Fallback pour web si exécuté via expo web
            return await SecureStore.getItemAsync(key)
        }
        return await AsyncStorage.getItem(key)
    }

    async setItem(key: string, value: string): Promise<void> {
        if (this.secureKeys.includes(key)) {
            if (Platform.OS === 'web') return AsyncStorage.setItem(key, value)
            await SecureStore.setItemAsync(key, value)
        } else {
            await AsyncStorage.setItem(key, value)
        }
    }

    async removeItem(key: string): Promise<void> {
        if (this.secureKeys.includes(key)) {
            if (Platform.OS === 'web') return AsyncStorage.removeItem(key)
            await SecureStore.deleteItemAsync(key)
        } else {
            await AsyncStorage.removeItem(key)
        }
    }

    async clear(): Promise<void> {
        // Clear AsyncStorage standard
        await AsyncStorage.clear()

        // Clear SecureStore items individually
        for (const key of this.secureKeys) {
            if (Platform.OS !== 'web') {
                await SecureStore.deleteItemAsync(key)
            }
        }
    }
}
