/**
 * Composant Table
 */
import { ReactNode } from 'react'
import clsx from 'clsx'
import './Table.css'

export interface TableColumn<T = any> {
  key: string
  label: string
  header?: string // Alias pour label (compatibilité)
  render?: (value: any, row: T, index: number) => ReactNode
  align?: 'left' | 'center' | 'right'
}

export interface TableProps<T = any> {
  columns: TableColumn<T>[]
  data: T[]
  className?: string
  compact?: boolean
  onRowClick?: (row: T, index: number) => void
  keyExtractor?: (row: T, index: number) => string | number
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
                ? keyExtractor(row, rowIndex)
                : row.id || rowIndex
              return (
                <tr
                  key={key}
                  onClick={() => onRowClick?.(row, rowIndex)}
                  className={onRowClick ? 'table-row-clickable' : ''}
                >
                  {columns.map((column) => {
                    const value = row[column.key]
                    return (
                      <td
                        key={column.key}
                        className={`text-${column.align || 'left'}`}
                      >
                        {column.render
                          ? column.render(value, row, rowIndex)
                          : value ?? '-'}
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

