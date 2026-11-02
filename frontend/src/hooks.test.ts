import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ApiError } from './api/client'
import { usePolling } from './hooks'

const isDone = (stage: string) => stage === 'available'

describe('usePolling', () => {
  it('keeps polling through a transient retryable failure', async () => {
    const replies: Array<string | ApiError> = [
      'publishing',
      new ApiError(500, { code: 'internal_error', retryable: true }),
      'available',
    ]
    const tick = () => {
      const reply = replies.shift()!
      return reply instanceof ApiError ? Promise.reject(reply) : Promise.resolve(reply)
    }
    const { result } = renderHook(() => usePolling(tick, isDone, 5))
    await waitFor(() => expect(result.current.value).toBe('available'))
    expect(result.current.error).toBeNull()
  })

  it('surfaces a non-retryable failure at once', async () => {
    const denied = new ApiError(401, { code: 'admin_unauthorized', retryable: false })
    let calls = 0
    const tick = () => {
      calls += 1
      return Promise.reject(denied)
    }
    const { result } = renderHook(() => usePolling(tick, isDone, 5))
    await waitFor(() => expect(result.current.error).toBe(denied))
    expect(calls).toBe(1)
  })

  it('gives up after repeated retryable failures', async () => {
    const busy = new ApiError(500, { code: 'internal_error', retryable: true })
    let calls = 0
    const tick = () => {
      calls += 1
      return Promise.reject(busy)
    }
    const { result } = renderHook(() => usePolling(tick, isDone, 5))
    await waitFor(() => expect(result.current.error).toBe(busy))
    expect(calls).toBe(3)
  })
})
