import type { EventMessage } from '@/types/domain'

export interface EventStreamHandle {
  start(): void
  stop(): void
}

interface EventStreamOptions {
  reconnectDelayMs?: number
  onStatusChange?: (connected: boolean) => void
}

const DEFAULT_RECONNECT_DELAY = 2000

function buildWebSocketUrl(): string {
  const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim()

  if (configuredBase && typeof window !== 'undefined') {
    // Ensure base URL ends with / so path segments are appended, not replaced
    const baseWithSlash = configuredBase.endsWith('/') ? configuredBase : configuredBase + '/'
    const url = new URL(baseWithSlash + 'v1/ws/events', window.location.origin)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    return url.toString()
  }

  if (typeof window !== 'undefined') {
    const url = new URL('/v1/ws/events', window.location.origin)
    url.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return url.toString()
  }

  // Fallback for non-browser environments
  return '/v1/ws/events'
}

export function createEventStream(
  onEvent: (event: EventMessage) => void,
  options?: EventStreamOptions,
): EventStreamHandle {
  if (typeof window === 'undefined') {
    return {
      start() {
        /* no-op */
      },
      stop() {
        /* no-op */
      },
    }
  }

  const reconnectDelay = options?.reconnectDelayMs ?? DEFAULT_RECONNECT_DELAY
  let ws: WebSocket | null = null
  let reconnectHandle: ReturnType<typeof window.setTimeout> | null = null
  let stopped = false

  const setStatus = (value: boolean) => {
    options?.onStatusChange?.(value)
  }

  const cleanup = () => {
    if (reconnectHandle !== null) {
      window.clearTimeout(reconnectHandle)
      reconnectHandle = null
    }
    if (ws) {
      ws.onopen = null
      ws.onclose = null
      ws.onerror = null
      ws.onmessage = null
      ws = null
    }
  }

  const scheduleReconnect = () => {
    if (stopped || reconnectHandle !== null) {
      return
    }
    reconnectHandle = window.setTimeout(() => {
      reconnectHandle = null
      connect()
    }, reconnectDelay)
  }

  const connect = () => {
    if (stopped) {
      return
    }

    try {
      ws = new WebSocket(buildWebSocketUrl())
    } catch (error) {
      console.error('WS: failed to create connection', error)
      scheduleReconnect()
      return
    }

    ws.onopen = () => {
      setStatus(true)
    }

    ws.onclose = () => {
      setStatus(false)
      cleanup()
      scheduleReconnect()
    }

    ws.onerror = (event) => {
      console.error('WS: error', event)
    }

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as unknown
        if (isBatchPayload(payload)) {
          payload.batch.forEach((item) => onEvent(item))
        } else if (isEventMessage(payload)) {
          onEvent(payload)
        } else {
          console.warn('WS: unknown payload shape', payload)
        }
      } catch (error) {
        console.error('WS: failed to parse event', error)
      }
    }
  }

  return {
    start() {
      stopped = false
      connect()
    },
    stop() {
      stopped = true
      setStatus(false)
      cleanup()
      if (ws) {
        ws.close()
      }
    },
  }
}

interface EventBatchPayload {
  batch: EventMessage[]
}

function isBatchPayload(payload: unknown): payload is EventBatchPayload {
  return Boolean(
    payload &&
      typeof payload === 'object' &&
      Array.isArray((payload as EventBatchPayload).batch),
  )
}

function isEventMessage(payload: unknown): payload is EventMessage {
  return Boolean(
    payload &&
      typeof payload === 'object' &&
      'resource' in (payload as Record<string, unknown>) &&
      'action' in (payload as Record<string, unknown>),
  )
}
