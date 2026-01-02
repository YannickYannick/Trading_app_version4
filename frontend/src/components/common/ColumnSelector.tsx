/**
 * Composant pour sélectionner les colonnes à afficher
 */
import { useState, useEffect } from 'react'
import { X, Check, Eye, EyeOff } from 'lucide-react'
import './ColumnSelector.css'

export interface ColumnOption {
  key: string
  label: string
  defaultVisible?: boolean
}

interface ColumnSelectorProps {
  columns: ColumnOption[]
  visibleColumns: string[]
  onColumnsChange: (visibleKeys: string[]) => void
  storageKey?: string // Clé pour sauvegarder dans localStorage
}

export default function ColumnSelector({
  columns,
  visibleColumns,
  onColumnsChange,
  storageKey
}: ColumnSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedColumns, setSelectedColumns] = useState<string[]>(visibleColumns)

  useEffect(() => {
    setSelectedColumns(visibleColumns)
  }, [visibleColumns])

  // Charger depuis localStorage si disponible
  useEffect(() => {
    if (storageKey) {
      try {
        const saved = localStorage.getItem(storageKey)
        if (saved) {
          const parsed = JSON.parse(saved)
          if (Array.isArray(parsed) && parsed.length > 0) {
            setSelectedColumns(parsed)
            onColumnsChange(parsed)
          }
        }
      } catch (e) {
        console.error('Erreur lors du chargement des colonnes:', e)
      }
    }
  }, [storageKey, onColumnsChange])

  const handleToggleColumn = (key: string) => {
    const newSelected = selectedColumns.includes(key)
      ? selectedColumns.filter(k => k !== key)
      : [...selectedColumns, key]
    
    setSelectedColumns(newSelected)
  }

  const handleSelectAll = () => {
    setSelectedColumns(columns.map(c => c.key))
  }

  const handleDeselectAll = () => {
    setSelectedColumns([])
  }

  const handleReset = () => {
    const defaultVisible = columns
      .filter(c => c.defaultVisible !== false)
      .map(c => c.key)
    setSelectedColumns(defaultVisible)
  }

  const handleApply = () => {
    onColumnsChange(selectedColumns)
    if (storageKey) {
      try {
        localStorage.setItem(storageKey, JSON.stringify(selectedColumns))
      } catch (e) {
        console.error('Erreur lors de la sauvegarde des colonnes:', e)
      }
    }
    setIsOpen(false)
  }

  const handleCancel = () => {
    setSelectedColumns(visibleColumns)
    setIsOpen(false)
  }

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="column-selector-btn"
        title="Sélectionner les colonnes à afficher"
      >
        <Eye style={{ width: '16px', height: '16px', marginRight: '4px' }} />
        Colonnes
      </button>

      {isOpen && (
        <div className="column-selector-overlay" onClick={handleCancel}>
          <div className="column-selector-modal" onClick={(e) => e.stopPropagation()}>
            <div className="column-selector-header">
              <h3>Sélectionner les colonnes à afficher</h3>
              <button
                onClick={handleCancel}
                className="column-selector-close"
                aria-label="Fermer"
              >
                <X style={{ width: '20px', height: '20px' }} />
              </button>
            </div>

            <div className="column-selector-actions">
              <button onClick={handleSelectAll} className="btn-link">
                Tout sélectionner
              </button>
              <button onClick={handleDeselectAll} className="btn-link">
                Tout désélectionner
              </button>
              <button onClick={handleReset} className="btn-link">
                Réinitialiser
              </button>
            </div>

            <div className="column-selector-list">
              {columns.map((column) => {
                const isSelected = selectedColumns.includes(column.key)
                return (
                  <label
                    key={column.key}
                    className={`column-selector-item ${isSelected ? 'selected' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => handleToggleColumn(column.key)}
                      className="column-selector-checkbox"
                    />
                    <span className="column-selector-label">{column.label}</span>
                    {isSelected && (
                      <Check style={{ width: '16px', height: '16px', color: '#22c55e' }} />
                    )}
                  </label>
                )
              })}
            </div>

            <div className="column-selector-footer">
              <button onClick={handleCancel} className="btn btn-secondary">
                Annuler
              </button>
              <button onClick={handleApply} className="btn btn-primary">
                Appliquer
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}








