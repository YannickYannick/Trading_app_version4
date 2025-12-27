/**
 * Composant Card
 */
import { ReactNode } from 'react'
import clsx from 'clsx'
import './Card.css'

export interface CardProps {
  title?: string
  subtitle?: string
  actions?: ReactNode
  footer?: ReactNode
  children: ReactNode
  className?: string
  hover?: boolean
}

export default function Card({
  title,
  subtitle,
  actions,
  footer,
  children,
  className,
  hover = true,
}: CardProps) {
  return (
    <div className={clsx('card', !hover && 'card-no-hover', className)}>
      {(title || subtitle || actions) && (
        <div className="card-header">
          <div className="card-header-content">
            {title && <h3 className="card-title">{title}</h3>}
            {subtitle && <p className="card-subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="card-actions">{actions}</div>}
        </div>
      )}
      <div className="card-body">{children}</div>
      {footer && <div className="card-footer">{footer}</div>}
    </div>
  )
}

