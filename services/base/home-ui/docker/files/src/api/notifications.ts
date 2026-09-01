import { httpClient } from '@kaapana/base-ui'

const KAAPANA_NOTIFICATION_ENDPOINT =
  import.meta.env.VITE_APP_NOTIFICATIONS_API_ENDPOINT || '/notifications'

export type NotificationID = string

export interface KaapanaNotification {
  topic: string
  title: string
  description: string
  icon: string
  link: string
  id: string
  timestamp: Date
}

export enum NotificationEventType {
  NEW = 'new',
  READ = 'read',
}

export interface NotificationEvent {
  id: string
  type: NotificationEventType
}

export async function fetchNotifications(params?: { limit?: number; cursor?: string | null }): Promise<{
  data: KaapanaNotification[]
  meta: {
    nextCursor: string | null
    hasMore: boolean
    total: number
  }
}> {
  const res = await httpClient.get(`${KAAPANA_NOTIFICATION_ENDPOINT}/v2/`, { params })
  return res.data
}

export async function readNotification(id: NotificationID) {
  return await httpClient.put(`${KAAPANA_NOTIFICATION_ENDPOINT}/v2/${id}/read`)
}

export class NotificationWebsocket {
  // Reconnect after an unexpected drop (service restart, proxy idle-timeout) with
  // a capped exponential backoff, so a persistently unreachable endpoint neither
  // hammers the server nor leaves live notifications dead for the rest of the session.
  private static readonly BASE_RECONNECT_DELAY_MS = 1000
  private static readonly MAX_RECONNECT_DELAY_MS = 30000
  // Only reset the backoff once a socket has stayed open this long, so a server that
  // accepts the upgrade then immediately drops it still backs off instead of
  // reconnecting at the base delay forever.
  private static readonly STABILITY_WINDOW_MS = 30000

  private readonly url: string
  private connection: WebSocket | null = null
  private readonly messageHandlers: ((event: NotificationEvent) => void)[] = []
  private readonly openHandlers: ((ev: Event) => void)[] = []
  private readonly closeHandlers: ((ev: CloseEvent) => void)[] = []
  private readonly errorHandlers: ((ev: Event) => void)[] = []
  private reconnectAttempts = 0
  private reconnectTimer: number | null = null
  private stabilityTimer: number | null = null
  private closedByClient = false

  constructor(notificationsEndpoint: string = KAAPANA_NOTIFICATION_ENDPOINT) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = window.location.host
    this.url = `${wsProtocol}//${wsHost}${notificationsEndpoint}/ws`
    this.open()
  }

  private open(): void {
    const socket = new WebSocket(this.url)
    this.connection = socket
    // A dead socket can still emit a late open/message/close/error after we have
    // reconnected; ignoring events from a socket that is no longer the current one
    // keeps registered handlers correct and prevents a second, leaking reconnect.
    socket.addEventListener('open', (ev: Event) => {
      if (socket !== this.connection) return
      this.stabilityTimer = window.setTimeout(() => {
        if (socket === this.connection) this.reconnectAttempts = 0
      }, NotificationWebsocket.STABILITY_WINDOW_MS)
      this.openHandlers.forEach((h) => h(ev))
    })
    socket.addEventListener('message', (e: MessageEvent) => {
      if (socket !== this.connection) return
      const event = JSON.parse(e.data)
      this.messageHandlers.forEach((h) => h(event))
    })
    socket.addEventListener('close', (ev: CloseEvent) => {
      if (socket !== this.connection) return
      this.clearStabilityTimer()
      this.closeHandlers.forEach((h) => h(ev))
      this.scheduleReconnect()
    })
    socket.addEventListener('error', (ev: Event) => {
      if (socket !== this.connection) return
      this.clearStabilityTimer()
      this.errorHandlers.forEach((h) => h(ev))
      this.scheduleReconnect()
    })
  }

  private clearStabilityTimer(): void {
    if (this.stabilityTimer !== null) {
      window.clearTimeout(this.stabilityTimer)
      this.stabilityTimer = null
    }
  }

  private scheduleReconnect(): void {
    if (this.closedByClient || this.reconnectTimer !== null) return
    const delay = Math.min(
      NotificationWebsocket.MAX_RECONNECT_DELAY_MS,
      NotificationWebsocket.BASE_RECONNECT_DELAY_MS * 2 ** this.reconnectAttempts,
    )
    this.reconnectAttempts += 1
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      this.open()
    }, delay)
  }

  public onMessage(handler: (event: NotificationEvent) => void): void {
    this.messageHandlers.push(handler)
  }

  public onOpen(handler: (ev: Event) => void): void {
    this.openHandlers.push(handler)
  }

  public onClose(handler: (ev: CloseEvent) => void): void {
    this.closeHandlers.push(handler)
  }

  public onError(handler: (ev: Event) => void): void {
    this.errorHandlers.push(handler)
  }

  // Intentional teardown: stop reconnecting and drop any pending timer/socket so
  // neither leaks past the caller's lifetime.
  public close(): void {
    this.closedByClient = true
    this.clearStabilityTimer()
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.connection?.close()
  }
}
