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
  cellType?: 'text' | 'number' | 'select' | 'checkbox' // Type de cellule éditable
  selectOptions?: Array<{ value: any; label: string }> // Options pour select
}

export interface TableProps<T = any> {
  columns: TableColumn<T>[]
  data: T[]
  className?: string
  compact?: boolean
  onRowClick?: (row: T, index: number) => void
  keyExtractor?: (row: T, index: number) => string | number
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

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      if (inputRef.current instanceof HTMLInputElement || inputRef.current instanceof HTMLTextAreaElement) {
        inputRef.current.select()
      }
    }
  }, [isEditing])

  const handleDoubleClick = () => {
    if (column.editable && !isEditing) {
      setIsEditing(true)
      // Pour les selects, utiliser la valeur du row directement
      const initialValue = column.cellType === 'select' && column.key 
        ? String(row[column.key] || value || '')
        : value
      setEditValue(initialValue)
    }
  }

  const handleBlur = async () => {
    if (isEditing) {
      setIsEditing(false)
      if (editValue !== value && onEdit) {
        try {
          await onEdit(editValue, row, column.key)
        } catch (error) {
          console.error('Erreur lors de l\'édition:', error)
          setEditValue(value) // Revenir à la valeur originale en cas d'erreur
        }
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleBlur()
    } else if (e.key === 'Escape') {
      setEditValue(value)
      setIsEditing(false)
    }
  }

  if (!column.editable || !isEditing) {
    return (
      <div
        onDoubleClick={handleDoubleClick}
        style={{
          cursor: column.editable ? 'pointer' : 'default',
          minHeight: '1.5rem',
        }}
        title={column.editable ? 'Double-cliquer pour éditer' : ''}
      >
        {column.render ? column.render(value, row, rowIndex) : value ?? '-'}
      </div>
    )
  }

  // Rendu de l'input d'édition
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
}: TableProps<T>) {
  return (
    <div className="table-wrapper">
      <table className={clsx('table', compact && 'table-compact', className)}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={`text-${column.align || 'left'}`}
              >
                {column.header || column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="table-empty">
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
                  onClick={() => onRowClick?.(row, rowIndex)}
                  className={onRowClick ? 'table-row-clickable' : ''}
                >
                  {columns.map((column) => {
                    // Pour les selects, utiliser la bonne clé (asset_id, broker_account_id, etc.)
                    let value = row[column.key]
                    if (column.key === 'asset_id' && !value) {
                      value = row['asset']?.id
                    }
                    if (column.key === 'broker_account_id' && !value) {
                      value = row['broker_account']?.id
                    }
                    return (
                      <td
                        key={column.key}
                        className={`text-${column.align || 'left'}`}
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

