/**
 * Composant Button
 */
import { ButtonHTMLAttributes, ReactNode } from 'react'
import clsx from 'clsx'
import './Button.css'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'buy' | 'sell' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  children: ReactNode
  fullWidth?: boolean
  isLoading?: boolean
  loadingText?: string
}

export default function Button({
  variant = 'primary',
  size = 'md',
  className,
  children,
  fullWidth = false,
  isLoading = false,
  loadingText,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={clsx(
        'btn',
        `btn-${variant}`,
        size !== 'md' && `btn-${size}`,
        fullWidth && 'btn-full-width',
        isLoading && 'btn-loading',
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <>
          <span className="btn-spinner" />
          {loadingText || children}
        </>
      ) : (
        children
      )}
    </button>
  )
}

