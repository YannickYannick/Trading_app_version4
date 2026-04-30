/**
 * Composant Badge
 */
import { ReactNode } from 'react'
import clsx from 'clsx'
import './Badge.css'

export interface BadgeProps {
  variant?: 'success' | 'danger' | 'warning' | 'info' | 'primary' | 'outline' | 'secondary'
  size?: 'small' | 'medium'
  children: ReactNode
  className?: string
}

export default function Badge({ variant = 'primary', size = 'medium', children, className }: BadgeProps) {
  return (
    <span className={clsx('badge', `badge-${variant}`, size === 'small' && 'badge-small', className)}>
      {children}
    </span>
  )
}

