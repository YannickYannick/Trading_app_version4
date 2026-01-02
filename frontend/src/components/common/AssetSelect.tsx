/**
 * Composant de sélection d'asset avec recherche et autocomplétion
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import type { AllAsset } from '@types'
import { assetService } from '@services/assets'
import './AssetSelect.css'

interface AssetSelectProps {
  value: number | null
  options?: AllAsset[] // Options statiques (optionnel)
  onChange: (value: number | null) => void
  onBlur?: () => void
  placeholder?: string
  useApiAutocomplete?: boolean // Si true, utilise l'API pour l'autocomplétion
}

export default function AssetSelect({
  value,
  options = [],
  onChange,
  onBlur,
  placeholder = 'Rechercher un asset...',
  useApiAutocomplete = true,
}: AssetSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filteredOptions, setFilteredOptions] = useState<AllAsset[]>(options)
  const [loading, setLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Recherche avec API si activée
  const searchAssets = useCallback(async (term: string) => {
    if (!term || term.length < 2) {
      setFilteredOptions(options)
      return
    }

    setLoading(true)
    try {
      // Utiliser l'API d'autocomplétion si disponible
      const results = await assetService.searchAllAssets(term)
      setFilteredOptions(results)
    } catch (err) {
      console.error('Erreur lors de la recherche d\'assets:', err)
      // Fallback sur les options locales
      const filtered = options.filter(asset => {
        const searchLower = term.toLowerCase()
        return (
          asset.symbol.toLowerCase().includes(searchLower) ||
          asset.name.toLowerCase().includes(searchLower) ||
          (asset.symbole_yahoo && asset.symbole_yahoo.toLowerCase().includes(searchLower))
        )
      })
      setFilteredOptions(filtered)
    } finally {
      setLoading(false)
    }
  }, [options, useApiAutocomplete])

  // Gérer la recherche avec debounce
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    if (useApiAutocomplete && isOpen) {
      searchTimeoutRef.current = setTimeout(() => {
        searchAssets(searchTerm)
      }, 300) // Debounce de 300ms
    } else if (!useApiAutocomplete) {
      // Filtrer localement
      if (!searchTerm) {
        setFilteredOptions(options)
      } else {
        const filtered = options.filter(asset => {
          const term = searchTerm.toLowerCase()
          return (
            asset.symbol.toLowerCase().includes(term) ||
            asset.name.toLowerCase().includes(term) ||
            (asset.symbole_yahoo && asset.symbole_yahoo.toLowerCase().includes(term))
          )
        })
        setFilteredOptions(filtered)
      }
    }

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [searchTerm, isOpen, useApiAutocomplete, searchAssets, options])

  // Mettre à jour les options filtrées quand options change
  useEffect(() => {
    if (!useApiAutocomplete && !searchTerm) {
      setFilteredOptions(options)
    }
  }, [options, useApiAutocomplete, searchTerm])

  // Trouver l'asset sélectionné (dans options ou filteredOptions)
  const selectedAsset = options.find(a => a.id === value) || filteredOptions.find(a => a.id === value)
  
  // Charger l'asset sélectionné depuis l'API si nécessaire
  useEffect(() => {
    if (value && !selectedAsset && useApiAutocomplete) {
      assetService.getAllAssetById(value).then(asset => {
        setFilteredOptions(prev => {
          // Ajouter l'asset à la liste s'il n'y est pas déjà
          if (!prev.find(a => a.id === asset.id)) {
            return [asset, ...prev]
          }
          return prev
        })
      }).catch(err => {
        console.error('Erreur lors du chargement de l\'asset:', err)
      })
    }
  }, [value, selectedAsset, useApiAutocomplete])

  // Fermer quand on clique en dehors
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSearchTerm('')
        onBlur?.()
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [isOpen, onBlur])

  // Focus sur l'input quand on ouvre
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const handleSelect = (assetId: number) => {
    onChange(assetId)
    setIsOpen(false)
    setSearchTerm('')
  }

  return (
    <div className="asset-select" ref={containerRef}>
      <div
        className="asset-select-trigger"
        onClick={() => setIsOpen(!isOpen)}
      >
        {selectedAsset ? (
          <span>{selectedAsset.symbol} - {selectedAsset.name}</span>
        ) : (
          <span className="text-muted">{placeholder}</span>
        )}
        <span className="asset-select-arrow">▼</span>
      </div>

      {isOpen && (
        <div className="asset-select-dropdown">
          <input
            ref={inputRef}
            type="text"
            className="asset-select-search"
            placeholder="Rechercher..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onClick={(e) => e.stopPropagation()}
          />
          <div className="asset-select-options">
            {filteredOptions.length === 0 ? (
              <div className="asset-select-no-results">Aucun résultat</div>
            ) : (
              filteredOptions.slice(0, 100).map((asset) => (
                <div
                  key={asset.id}
                  className={`asset-select-option ${value === asset.id ? 'selected' : ''}`}
                  onClick={() => handleSelect(asset.id)}
                >
                  <div className="asset-select-option-symbol">{asset.symbol}</div>
                  <div className="asset-select-option-name">{asset.name}</div>
                  {asset.symbole_yahoo && asset.symbole_yahoo !== 'Not_searched' && asset.symbole_yahoo !== 'not_found' && (
                    <div className="asset-select-option-yahoo">Yahoo: {asset.symbole_yahoo}</div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

