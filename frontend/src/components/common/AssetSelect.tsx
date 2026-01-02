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

  // Type pour les résultats d'autocomplétion
  type AutocompleteAsset = {
    id: number
    symbol: string
    name: string
    platform: string
    asset_type?: string
    currency?: string
    market?: string
    text?: string
    saxo_uic?: number
  }

  const [autocompleteResults, setAutocompleteResults] = useState<AutocompleteAsset[]>([])

  // Recherche avec API si activée (même API que PlaceOrderModal)
  const searchAssets = useCallback(async (term: string) => {
    if (!term || term.length < 1) {
      setAutocompleteResults([])
      setFilteredOptions(options)
      return
    }

    setLoading(true)
    try {
      // Utiliser l'API d'autocomplétion (même que PlaceOrderModal)
      const results = await assetService.autocompleteAllAssets(term)
      setAutocompleteResults(results)
      // Convertir les résultats en format AllAsset pour compatibilité
      const convertedResults: AllAsset[] = results.map(r => ({
        id: r.id,
        symbol: r.symbol,
        name: r.name,
        symbole_yahoo: null,
        asset_type: r.asset_type || '',
        currency: r.currency || '',
        market: r.market || '',
        platform: r.platform,
      } as AllAsset))
      setFilteredOptions(convertedResults)
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
      setAutocompleteResults([])
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
            {loading ? (
              <div className="asset-select-loading">Chargement...</div>
            ) : autocompleteResults.length === 0 && filteredOptions.length === 0 ? (
              <div className="asset-select-no-results">
                {searchTerm ? 'Aucun résultat' : 'Tapez pour rechercher...'}
              </div>
            ) : (
              // Afficher les résultats d'autocomplétion si disponibles (même format que PlaceOrderModal)
              (autocompleteResults.length > 0 
                ? autocompleteResults.map((asset) => (
                    <div
                      key={asset.id}
                      className={`asset-select-option autocomplete-item ${value === asset.id ? 'selected' : ''}`}
                      onClick={() => handleSelect(asset.id)}
                      onMouseDown={(e) => e.preventDefault()} // Empêcher le blur
                    >
                      <div className="asset-select-option-symbol autocomplete-symbol">{asset.symbol}</div>
                      <div className="asset-select-option-name autocomplete-name">{asset.name}</div>
                      {asset.platform && (
                        <div className="asset-select-option-platform autocomplete-platform">{asset.platform}</div>
                      )}
                    </div>
                  ))
                : filteredOptions.slice(0, 100).map((asset) => (
                    <div
                      key={asset.id}
                      className={`asset-select-option autocomplete-item ${value === asset.id ? 'selected' : ''}`}
                      onClick={() => handleSelect(asset.id)}
                      onMouseDown={(e) => e.preventDefault()} // Empêcher le blur
                    >
                      <div className="asset-select-option-symbol autocomplete-symbol">{asset.symbol}</div>
                      <div className="asset-select-option-name autocomplete-name">{asset.name}</div>
                      {asset.platform && (
                        <div className="asset-select-option-platform autocomplete-platform">{asset.platform}</div>
                      )}
                    </div>
                  ))
              )
            )}
          </div>
        </div>
      )}
    </div>
  )
}

