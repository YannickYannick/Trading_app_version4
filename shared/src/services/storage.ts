/**
 * Interface pour l'adaptateur de stockage
 * Permet d'abstraire localStorage (Web) vs AsyncStorage/SecureStore (Mobile)
 */
export interface StorageAdapter {
    getItem(key: string): Promise<string | null> | string | null
    setItem(key: string, value: string): Promise<void> | void
    removeItem(key: string): Promise<void> | void
    clear(): Promise<void> | void
}

/**
 * Adaptateur localStorage pour le Web
 */
export class LocalStorageAdapter implements StorageAdapter {
    getItem(key: string): string | null {
        if (typeof window === 'undefined') return null
        return localStorage.getItem(key)
    }

    setItem(key: string, value: string): void {
        if (typeof window !== 'undefined') {
            localStorage.setItem(key, value)
        }
    }

    removeItem(key: string): void {
        if (typeof window !== 'undefined') {
            localStorage.removeItem(key)
        }
    }

    clear(): void {
        if (typeof window !== 'undefined') {
            localStorage.clear()
        }
    }
}
