/**
 * Composant de sélection d'asset avec recherche
 */
import { useState, useRef, useEffect } from 'react'
import type { AllAsset } from '@types'
import './AssetSelect.css'

interface AssetSelectProps {
  value: number | null
  options: AllAsset[]
  onChange: (value: number | null) => void
  onBlur?: () => void
  placeholder?: string
}

export default function AssetSelect({
  value,
  options,
  onChange,
  onBlur,
  placeholder = 'Rechercher un asset...'
}: AssetSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Filtrer les options selon le terme de recherche
  const filteredOptions = options.filter(asset => {
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return (
      asset.symbol.toLowerCase().includes(term) ||
      asset.name.toLowerCase().includes(term) ||
      (asset.symbole_yahoo && asset.symbole_yahoo.toLowerCase().includes(term))
    )
  })

  // Trouver l'asset sélectionné
  const selectedAsset = options.find(a => a.id === value)

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
                  {asset.symbole_yahoo && (
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

