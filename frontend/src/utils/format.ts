/**
 * Utilitaires de formatage
 */
import { format, formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale/fr'

/**
 * Formate un montant en devise
 */
export function formatCurrency(
  value: number | null | undefined,
  currency: string = 'USD',
  decimals: number = 2
): string {
  if (value === null || value === undefined) return '-'
  
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

/**
 * Formate un pourcentage
 */
export function formatPercent(
  value: number | null | undefined,
  decimals: number = 2
): string {
  if (value === null || value === undefined) return '-'
  
  // Convertir en nombre si ce n'est pas déjà le cas
  const numValue = typeof value === 'string' ? parseFloat(value) : value
  
  // Vérifier si c'est un nombre valide
  if (isNaN(numValue) || !isFinite(numValue)) return '-'
  
  return `${numValue >= 0 ? '+' : ''}${numValue.toFixed(decimals)}%`
}

/**
 * Formate une date
 */
export function formatDate(
  date: string | Date | null | undefined,
  formatStr: string = 'dd/MM/yyyy HH:mm'
): string {
  if (!date) return '-'
  
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date
    return format(dateObj, formatStr, { locale: fr })
  } catch {
    return '-'
  }
}

/**
 * Formate une date relative (il y a X)
 */
export function formatDateRelative(
  date: string | Date | null | undefined
): string {
  if (!date) return '-'
  
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date
    return formatDistanceToNow(dateObj, { addSuffix: true, locale: fr })
  } catch {
    return '-'
  }
}

/**
 * Formate un nombre avec séparateurs
 */
export function formatNumber(
  value: number | null | undefined,
  decimals: number = 2
): string {
  if (value === null || value === undefined) return '-'
  
  return new Intl.NumberFormat('fr-FR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

/**
 * Formate une taille de position
 */
export function formatSize(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  return formatNumber(value, 4)
}

