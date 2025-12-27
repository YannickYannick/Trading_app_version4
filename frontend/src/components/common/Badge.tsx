/**
 * Composant Badge
 */
import { ReactNode } from 'react'
import clsx from 'clsx'
import './Badge.css'

export interface BadgeProps {
  variant?: 'success' | 'danger' | 'warning' | 'info' | 'primary' | 'outline'
  children: ReactNode
  className?: string
}

export default function Badge({ variant = 'primary', children, className }: BadgeProps) {
  return (
    <span className={clsx('badge', `badge-${variant}`, className)}>
      {children}
    </span>
  )
}

