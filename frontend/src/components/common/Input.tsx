/**
 * Composant Input
 */
import { InputHTMLAttributes, forwardRef } from 'react'
import clsx from 'clsx'
import './Input.css'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  fullWidth?: boolean
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className, fullWidth = false, ...props }, ref) => {
    return (
      <div className={clsx('input-group', fullWidth && 'input-group-full-width')}>
        {label && (
          <label className="input-label" htmlFor={props.id}>
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={clsx('input', error && 'input-error', className)}
          {...props}
        />
        {error && <span className="input-error-message">{error}</span>}
        {helperText && !error && (
          <span className="input-helper-text">{helperText}</span>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

export default Input

