/**
 * Composant Loading
 */
import './Loading.css'

export interface LoadingProps {
  size?: 'sm' | 'md' | 'lg'
  text?: string
  fullScreen?: boolean
  className?: string
}

export default function Loading({
  size = 'md',
  text,
  fullScreen = false,
  className,
}: LoadingProps) {
  const content = (
    <div className={`loading-wrapper ${fullScreen ? 'loading-fullscreen' : ''} ${className || ''}`}>
      <div className={['loading-spinner', `loading-${size}`].join(' ')} />
      {text && <p className="loading-text">{text}</p>}
    </div>
  )

  return content
}

