import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from './api/client'

/** Consecutive retryable polling failures tolerated (with backoff) before surfacing the error. */
const MAX_TRANSIENT_FAILURES = 3

export interface AsyncState<T> {
  data: T | null
  error: unknown
  loading: boolean
  reload: () => void
}

/** Loads data on mount and whenever `load` changes; stale responses are discarded. */
export function useAsync<T>(load: (() => Promise<T>) | null): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(load !== null)
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    if (!load) return
    let current = true
    setLoading(true)
    setError(null)
    load()
      .then((value) => current && setData(value))
      .catch((reason: unknown) => current && setError(reason))
      .finally(() => current && setLoading(false))
    return () => {
      current = false
    }
  }, [load, nonce])

  const reload = useCallback(() => setNonce((value) => value + 1), [])
  return { data, error, loading, reload }
}

/**
 * Polls `tick` every `intervalMs` until it reports completion. Polling keeps the job model
 * unchanged; a server-sent-events transport can replace it later.
 */
export function usePolling<T>(
  tick: (() => Promise<T>) | null,
  isDone: (value: T) => boolean,
  intervalMs = 2000,
): { value: T | null; error: unknown } {
  const [value, setValue] = useState<T | null>(null)
  const [error, setError] = useState<unknown>(null)
  const done = useRef(isDone)
  useEffect(() => {
    done.current = isDone
  }, [isDone])

  useEffect(() => {
    if (!tick) return
    let active = true
    let timer: ReturnType<typeof setTimeout> | undefined
    setValue(null)
    setError(null)
    let failures = 0
    const run = async () => {
      try {
        const next = await tick()
        if (!active) return
        failures = 0
        setValue(next)
        if (!done.current(next)) timer = setTimeout(run, intervalMs)
      } catch (reason) {
        if (!active) return
        // A transient failure must not abandon a job that keeps progressing on the server.
        failures += 1
        if (reason instanceof ApiError && reason.retryable && failures < MAX_TRANSIENT_FAILURES) {
          timer = setTimeout(run, intervalMs * 2 ** failures)
          return
        }
        setError(reason)
      }
    }
    void run()
    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [tick, intervalMs])

  return { value, error }
}
