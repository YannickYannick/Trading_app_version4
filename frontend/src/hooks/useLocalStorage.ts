/**
 * Hook pour gérer le localStorage de manière réactive
 * Permet de synchroniser l'état React avec le localStorage
 */
import { useState, useEffect, useCallback } from 'react'

/**
 * Hook pour utiliser le localStorage avec React
 * @param key - La clé dans le localStorage
 * @param initialValue - La valeur initiale si la clé n'existe pas
 * @returns [storedValue, setValue] - Similaire à useState
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((val: T) => T)) => void] {
  // État pour stocker la valeur
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      // Récupérer depuis le localStorage
      const item = window.localStorage.getItem(key)
      // Parser la valeur JSON ou retourner la valeur initiale
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      // En cas d'erreur, retourner la valeur initiale
      console.error(`Erreur lors de la lecture du localStorage pour la clé "${key}":`, error)
      return initialValue
    }
  })

  // Fonction pour mettre à jour la valeur
  const setValue = useCallback(
    (value: T | ((val: T) => T)) => {
      try {
        // Permettre à value d'être une fonction pour avoir la même API que useState
        const valueToStore = value instanceof Function ? value(storedValue) : value
        // Sauvegarder l'état
        setStoredValue(valueToStore)
        // Sauvegarder dans le localStorage
        window.localStorage.setItem(key, JSON.stringify(valueToStore))
      } catch (error) {
        console.error(`Erreur lors de l'écriture dans le localStorage pour la clé "${key}":`, error)
      }
    },
    [key, storedValue]
  )

  // Écouter les changements du localStorage depuis d'autres onglets
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === key && e.newValue) {
        try {
          setStoredValue(JSON.parse(e.newValue))
        } catch (error) {
          console.error(`Erreur lors de la synchronisation du localStorage pour la clé "${key}":`, error)
        }
      }
    }

    window.addEventListener('storage', handleStorageChange)
    return () => {
      window.removeEventListener('storage', handleStorageChange)
    }
  }, [key])

  return [storedValue, setValue]
}

