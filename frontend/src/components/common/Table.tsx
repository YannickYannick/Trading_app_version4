/**
 * Composant Table
 */
import { ReactNode, useState, useRef, useEffect } from 'react'
import clsx from 'clsx'
import './Table.css'

export interface TableColumn<T = any> {
  key: string
  label: string
  header?: string // Alias pour label (compatibilité)
  render?: (value: any, row: T, index: number) => ReactNode
  align?: 'left' | 'center' | 'right'
  editable?: boolean // Si la colonne est éditable
  onCellEdit?: (value: any, row: T, key: string) => void | Promise<void> // Callback lors de l'édition
  cellType?: 'text' | 'number' | 'select' | 'checkbox' | 'range' // Type de cellule éditable
  selectOptions?: Array<{ value: any; label: string }> // Options pour select
  rangeFields?: { min: string; max: string } // Pour cellType='range' : les clés des champs min et max
  width?: string | number // Largeur de la colonne (px, %, auto, etc.)
  minWidth?: string | number // Largeur minimale
  maxWidth?: string | number // Largeur maximale
}

export interface TableProps<T = any> {
  columns: TableColumn<T>[]
  data: T[]
  className?: string
  compact?: boolean
  onRowClick?: (row: T, index: number) => void
  keyExtractor?: (row: T, index: number) => string | number
  sortConfig?: { key: string; direction: 'asc' | 'desc' } | null
  onSort?: (key: string) => void
  visibleColumns?: string[] // Colonnes à afficher (si vide, toutes sont affichées)
}

function EditableCell<T extends Record<string, any>>({
  value,
  row,
  column,
  rowIndex,
  onEdit,
}: {
  value: any
  row: T
  column: TableColumn<T>
  rowIndex: number
  onEdit?: (value: any, row: T, key: string) => void | Promise<void>
}) {
  const [isEditing, setIsEditing] = useState(false)
  // Pour les selects, utiliser la valeur du row directement pour avoir la bonne clé
  const initialValue = column.cellType === 'select' && column.key 
    ? String(row[column.key] || value || '')
    : value
  const [editValue, setEditValue] = useState(initialValue)
  const inputRef = useRef<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(null)
  const minInputRef = useRef<HTMLInputElement>(null)
  const maxInputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isEditing) {
      if (column.cellType === 'range' && minInputRef.current) {
        minInputRef.current.focus()
        minInputRef.current.select()
      } else if (inputRef.current) {
        inputRef.current.focus()
        if (inputRef.current instanceof HTMLInputElement || inputRef.current instanceof HTMLTextAreaElement) {
          inputRef.current.select()
        }
      }
    }
  }, [isEditing, column.cellType])

  const handleDoubleClick = () => {
    if (column.editable && !isEditing) {
      setIsEditing(true)
      // Pour les selects, utiliser la valeur du row directement
      if (column.cellType === 'select' && column.key) {
        setEditValue(String(row[column.key] || value || ''))
      } else if (column.cellType === 'range' && column.rangeFields) {
        // Pour les ranges, initialiser avec les valeurs min et max
        const minValue = column.rangeFields.min.includes('.') 
          ? row[column.rangeFields.min.split('.')[0]]?.[column.rangeFields.min.split('.')[1]]
          : row[column.rangeFields.min]
        const maxValue = column.rangeFields.max.includes('.') 
          ? row[column.rangeFields.max.split('.')[0]]?.[column.rangeFields.max.split('.')[1]]
          : row[column.rangeFields.max]
        setEditValue({
          min: minValue || '',
          max: maxValue || ''
        })
      } else {
        setEditValue(value)
      }
    }
  }

  const handleBlur = async (e?: React.FocusEvent) => {
    if (!isEditing) return
    
    // Pour les cellules de type range, vérifier si le focus reste dans le conteneur
    if (column.cellType === 'range' && e?.relatedTarget && containerRef.current) {
      // Si le focus va vers un autre élément dans le même conteneur, ne pas fermer l'édition
      if (containerRef.current.contains(e.relatedTarget as Node)) {
        return
      }
    }
    
    setIsEditing(false)
    // Pour les ranges, vérifier si les valeurs ont changé
    let hasChanged = false
    if (column.cellType === 'range' && column.rangeFields && typeof editValue === 'object') {
      const currentMin = column.rangeFields.min.includes('.') 
        ? row[column.rangeFields.min.split('.')[0]]?.[column.rangeFields.min.split('.')[1]]
        : row[column.rangeFields.min]
      const currentMax = column.rangeFields.max.includes('.') 
        ? row[column.rangeFields.max.split('.')[0]]?.[column.rangeFields.max.split('.')[1]]
        : row[column.rangeFields.max]
      hasChanged = editValue.min !== currentMin || editValue.max !== currentMax
    } else {
      hasChanged = editValue !== value
    }
    
    if (hasChanged && onEdit) {
      try {
        await onEdit(editValue, row, column.key)
      } catch (error) {
        console.error('Erreur lors de l\'édition:', error)
        // Revenir à la valeur originale en cas d'erreur
        if (column.cellType === 'range' && column.rangeFields) {
          const minValue = column.rangeFields.min.includes('.') 
            ? row[column.rangeFields.min.split('.')[0]]?.[column.rangeFields.min.split('.')[1]]
            : row[column.rangeFields.min]
          const maxValue = column.rangeFields.max.includes('.') 
            ? row[column.rangeFields.max.split('.')[0]]?.[column.rangeFields.max.split('.')[1]]
            : row[column.rangeFields.max]
          setEditValue({ min: minValue || '', max: maxValue || '' })
        } else {
          setEditValue(value)
        }
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      // Pour Enter, on force la fermeture sans vérifier le conteneur
      setIsEditing(false)
      // Sauvegarder les modifications
      let hasChanged = false
      if (column.cellType === 'range' && column.rangeFields && typeof editValue === 'object') {
        const currentMin = column.rangeFields.min.includes('.') 
          ? row[column.rangeFields.min.split('.')[0]]?.[column.rangeFields.min.split('.')[1]]
          : row[column.rangeFields.min]
        const currentMax = column.rangeFields.max.includes('.') 
          ? row[column.rangeFields.max.split('.')[0]]?.[column.rangeFields.max.split('.')[1]]
          : row[column.rangeFields.max]
        hasChanged = editValue.min !== currentMin || editValue.max !== currentMax
      } else {
        hasChanged = editValue !== value
      }
      if (hasChanged && onEdit) {
        onEdit(editValue, row, column.key)
      }
    } else if (e.key === 'Escape') {
      // Revenir à la valeur originale
      if (column.cellType === 'range' && column.rangeFields) {
        const minValue = column.rangeFields.min.includes('.') 
          ? row[column.rangeFields.min.split('.')[0]]?.[column.rangeFields.min.split('.')[1]]
          : row[column.rangeFields.min]
        const maxValue = column.rangeFields.max.includes('.') 
          ? row[column.rangeFields.max.split('.')[0]]?.[column.rangeFields.max.split('.')[1]]
          : row[column.rangeFields.max]
        setEditValue({ min: minValue || '', max: maxValue || '' })
      } else {
        setEditValue(value)
      }
      setIsEditing(false)
    } else if (e.key === 'Tab' && column.cellType === 'range' && editValue && typeof editValue === 'object') {
      // Tab pour naviguer entre Min et Max
      if (document.activeElement === minInputRef.current) {
        e.preventDefault()
        maxInputRef.current?.focus()
        maxInputRef.current?.select()
      }
    }
  }

  if (!column.editable || !isEditing) {
    const content = column.render ? column.render(value, row, rowIndex) : (value ?? '-')
    return (
      <div
        onDoubleClick={(e) => {
          e.stopPropagation() // Empêcher la propagation du double-clic
          handleDoubleClick()
        }}
        onClick={(e) => {
          // Empêcher la propagation du simple clic aussi pour les cellules éditables
          if (column.editable) {
            e.stopPropagation()
          }
        }}
        style={{
          cursor: column.editable ? 'pointer' : 'default',
          minHeight: '1.5rem',
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: column.align === 'right' ? 'flex-end' : column.align === 'center' ? 'center' : 'flex-start',
        }}
        title={column.editable ? 'Double-cliquer pour éditer' : ''}
      >
        {content}
      </div>
    )
  }

  // Rendu de l'input d'édition
  if (column.cellType === 'range' && column.rangeFields && typeof editValue === 'object') {
    return (
      <div 
        ref={containerRef}
        style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          gap: '4px',
          width: '100%',
          height: '100%',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '4px'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'center', width: '100%' }}>
          <span style={{ fontSize: '0.75rem', color: '#6b7280', minWidth: '35px' }}>Min:</span>
          <input
            ref={minInputRef}
            type="number"
            value={editValue.min ?? ''}
            onChange={(e) => setEditValue({ ...editValue, min: e.target.value })}
            onKeyDown={handleKeyDown}
            onBlur={handleBlur}
            className="table-cell-input"
            style={{ flex: 1, fontSize: '0.875rem', maxWidth: '80px' }}
            step="any"
            placeholder="Min"
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'center', width: '100%' }}>
          <span style={{ fontSize: '0.75rem', color: '#6b7280', minWidth: '35px' }}>Max:</span>
          <input
            ref={maxInputRef}
            type="number"
            value={editValue.max ?? ''}
            onChange={(e) => setEditValue({ ...editValue, max: e.target.value })}
            onKeyDown={handleKeyDown}
            onBlur={handleBlur}
            className="table-cell-input"
            style={{ flex: 1, fontSize: '0.875rem', maxWidth: '80px' }}
            step="any"
            placeholder="Max"
          />
        </div>
      </div>
    )
  }

  if (column.cellType === 'select' && column.selectOptions) {
    return (
      <select
        ref={inputRef as React.RefObject<HTMLSelectElement>}
        value={editValue ?? ''}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        className="table-cell-input"
        onClick={(e) => e.stopPropagation()}
      >
        {column.selectOptions.map((option) => (
          <option key={String(option.value)} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    )
  }

  if (column.cellType === 'checkbox') {
    return (
      <input
        type="checkbox"
        checked={!!editValue}
        onChange={(e) => {
          setEditValue(e.target.checked)
          handleBlur()
        }}
        className="table-cell-checkbox"
        onClick={(e) => e.stopPropagation()}
      />
    )
  }

  if (column.cellType === 'number') {
    return (
      <input
        ref={inputRef as React.RefObject<HTMLInputElement>}
        type="number"
        value={editValue ?? ''}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        className="table-cell-input"
        onClick={(e) => e.stopPropagation()}
        step="any"
      />
    )
  }

  // Par défaut : input text
  return (
    <input
      ref={inputRef as React.RefObject<HTMLInputElement>}
      type="text"
      value={editValue ?? ''}
      onChange={(e) => setEditValue(e.target.value)}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
      className="table-cell-input"
      onClick={(e) => e.stopPropagation()}
    />
  )
}

export default function Table<T extends Record<string, any>>({
  columns,
  data,
  className,
  compact = false,
  onRowClick,
  keyExtractor,
  sortConfig,
  onSort,
  visibleColumns,
}: TableProps<T>) {
  // Filtrer les colonnes selon visibleColumns
  const displayColumns = visibleColumns && visibleColumns.length > 0
    ? columns.filter(col => visibleColumns.includes(col.key))
    : columns
  
  return (
    <div className="table-wrapper">
      <table className={clsx('table', compact && 'table-compact', className)}>
        <thead>
          <tr>
            {displayColumns.map((column) => {
              const style: React.CSSProperties = {}
              if (column.width) {
                style.width = typeof column.width === 'number' ? `${column.width}px` : column.width
              }
              if (column.minWidth) {
                style.minWidth = typeof column.minWidth === 'number' ? `${column.minWidth}px` : column.minWidth
              }
              if (column.maxWidth) {
                style.maxWidth = typeof column.maxWidth === 'number' ? `${column.maxWidth}px` : column.maxWidth
              }
              
              return (
                <th
                  key={column.key}
                  className={`text-${column.align || 'center'} ${onSort ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800' : ''}`}
                  onClick={() => onSort?.(column.key)}
                  title={onSort ? 'Cliquer pour trier' : ''}
                  style={style}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: column.align === 'right' ? 'flex-end' : column.align === 'left' ? 'flex-start' : 'center', gap: '0.25rem' }}>
                    {column.header || column.label}
                    {onSort && sortConfig?.key === column.key && (
                      <span style={{ fontSize: '0.75rem' }}>
                        {sortConfig.direction === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </div>
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
                    <td colSpan={displayColumns.length} className="table-empty">
                Aucune donnée disponible
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => {
              const key = keyExtractor
                ? String(keyExtractor(row, rowIndex))
                : String(row.id || rowIndex)
              return (
                <tr
                  key={key}
                  onClick={(e) => {
                    // Ne pas déclencher onRowClick si on clique sur une cellule éditable
                    if (!e.target || !(e.target as HTMLElement).closest('.table-cell-editable')) {
                      onRowClick?.(row, rowIndex)
                    }
                  }}
                  className={onRowClick ? 'table-row-clickable' : ''}
                >
                  {displayColumns.map((column) => {
                    // Pour les selects, utiliser la bonne clé (asset_id, broker_account_id, etc.)
                    let value = row[column.key]
                    if (column.key === 'asset_id' && !value) {
                      value = row['asset']?.id
                    }
                    if (column.key === 'broker_account_id' && !value) {
                      value = row['broker_account']?.id
                    }
                    const cellStyle: React.CSSProperties = {}
                    if (column.width) {
                      cellStyle.width = typeof column.width === 'number' ? `${column.width}px` : column.width
                    }
                    if (column.minWidth) {
                      cellStyle.minWidth = typeof column.minWidth === 'number' ? `${column.minWidth}px` : column.minWidth
                    }
                    if (column.maxWidth) {
                      cellStyle.maxWidth = typeof column.maxWidth === 'number' ? `${column.maxWidth}px` : column.maxWidth
                    }
                    
                    return (
                      <td
                        key={column.key}
                        className={`text-${column.align || 'left'} ${column.editable ? 'table-cell-editable' : ''}`}
                        style={cellStyle}
                        onClick={(e) => {
                          // Empêcher la propagation pour les cellules éditables
                          if (column.editable) {
                            e.stopPropagation()
                          }
                        }}
                      >
                        {column.editable ? (
                          <EditableCell
                            value={value}
                            row={row}
                            column={column}
                            rowIndex={rowIndex}
                            onEdit={column.onCellEdit}
                          />
                        ) : (
                          column.render
                            ? column.render(value, row, rowIndex)
                            : value ?? '-'
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })
          )}
        </tbody>
      </table>
    </div>
  )
}

