/**
 * Tests pour le hook useErrorHandler
 */
import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useErrorHandler } from '../useErrorHandler'

describe('useErrorHandler', () => {
  it('should initialize with no error', () => {
    const { result } = renderHook(() => useErrorHandler())
    expect(result.current.hasError).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('should handle string error', () => {
    const { result } = renderHook(() => useErrorHandler())
    
    act(() => {
      result.current.handleError('Test error')
    })
    
    expect(result.current.hasError).toBe(true)
    expect(result.current.error).not.toBeNull()
    expect(result.current.error?.error).toBe('Test error')
  })

  it('should handle object error', () => {
    const { result } = renderHook(() => useErrorHandler())
    
    const error = {
      error: 'Error message',
      code: 'TEST_ERROR',
      message: 'Error message',
    }
    
    act(() => {
      result.current.handleError(error)
    })
    
    expect(result.current.hasError).toBe(true)
    expect(result.current.error?.code).toBe('TEST_ERROR')
  })

  it('should clear error', () => {
    const { result } = renderHook(() => useErrorHandler())
    
    act(() => {
      result.current.handleError('Test error')
    })
    
    expect(result.current.hasError).toBe(true)
    
    act(() => {
      result.current.clearError()
    })
    
    expect(result.current.hasError).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('should get error message', () => {
    const { result } = renderHook(() => useErrorHandler())
    
    act(() => {
      result.current.handleError('Test error')
    })
    
    expect(result.current.getErrorMessage()).toBe('Test error')
  })
})

