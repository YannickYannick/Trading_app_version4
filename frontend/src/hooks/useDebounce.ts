/**
 * Hook pour le debounce d'une valeur
 * Utile pour les recherches et autres inputs qui doivent être retardés
 */
import { useState, useEffect } from 'react'

/**
 * Retourne une version debounced de la valeur
 * @param value - La valeur à debouncer
 * @param delay - Le délai en millisecondes (défaut: 500ms)
 * @returns La valeur debounced
 */
export function useDebounce<T>(value: T, delay: number = 500): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    // Créer un timer qui met à jour la valeur debounced après le délai
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    // Nettoyer le timer si la valeur change avant la fin du délai
    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

