import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { NotificationWebsocket } from '@/api/notifications'

// The class constants (kept in sync with notifications.ts).
const BASE_RECONNECT_DELAY_MS = 1000
const MAX_RECONNECT_DELAY_MS = 30000
const STABILITY_WINDOW_MS = 30000

// A drop-in WebSocket stub: jsdom has no usable WebSocket, and we need to drive
// close/error/message events by hand and count how many sockets get opened.
class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  private listeners: Record<string, ((ev: unknown) => void)[]> = {}
  public close = vi.fn()

  constructor(public url: string) {
    FakeWebSocket.instances.push(this)
  }

  addEventListener(type: string, cb: (ev: unknown) => void): void {
    ;(this.listeners[type] ||= []).push(cb)
  }

  emit(type: string, ev: unknown = {}): void {
    ;(this.listeners[type] || []).forEach((cb) => cb(ev))
  }
}

const latest = () => FakeWebSocket.instances[FakeWebSocket.instances.length - 1]

describe('NotificationWebsocket reconnect', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    FakeWebSocket.instances = []
    vi.stubGlobal('WebSocket', FakeWebSocket)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('reconnects after the backoff when the socket drops unexpectedly', () => {
    new NotificationWebsocket()
    expect(FakeWebSocket.instances).toHaveLength(1)

    latest().emit('close', { code: 1006 })
    // No immediate reconnect: it waits out the backoff first.
    expect(FakeWebSocket.instances).toHaveLength(1)

    vi.advanceTimersByTime(BASE_RECONNECT_DELAY_MS - 1)
    expect(FakeWebSocket.instances).toHaveLength(1)
    vi.advanceTimersByTime(1)
    expect(FakeWebSocket.instances).toHaveLength(2)
  })

  it('also reconnects on an error event', () => {
    new NotificationWebsocket()
    latest().emit('error')
    vi.advanceTimersByTime(BASE_RECONNECT_DELAY_MS)
    expect(FakeWebSocket.instances).toHaveLength(2)
  })

  it('caps the backoff delay across repeated drops', () => {
    new NotificationWebsocket()
    // Never emitting `open` keeps the attempt counter growing past the point
    // where the doubling delay would exceed the cap.
    for (let i = 0; i < 7; i++) {
      latest().emit('close')
      vi.advanceTimersByTime(MAX_RECONNECT_DELAY_MS)
    }
    const countBeforeNextDrop = FakeWebSocket.instances.length

    latest().emit('close')
    // Uncapped, the delay here would be 1000 * 2**7 = 128000ms; the cap holds it
    // at exactly MAX_RECONNECT_DELAY_MS.
    vi.advanceTimersByTime(MAX_RECONNECT_DELAY_MS - 1)
    expect(FakeWebSocket.instances).toHaveLength(countBeforeNextDrop)
    vi.advanceTimersByTime(1)
    expect(FakeWebSocket.instances).toHaveLength(countBeforeNextDrop + 1)
  })

  it('resets the backoff only after the socket stays open for the stability window', () => {
    new NotificationWebsocket()
    latest().emit('open')
    // Stay open long enough to be treated as healthy, then drop.
    vi.advanceTimersByTime(STABILITY_WINDOW_MS)
    latest().emit('close')
    vi.advanceTimersByTime(BASE_RECONNECT_DELAY_MS)
    expect(FakeWebSocket.instances).toHaveLength(2)

    // The stable window reset the counter, so the next drop backs off from the
    // base delay again rather than from 2x.
    latest().emit('open')
    vi.advanceTimersByTime(STABILITY_WINDOW_MS)
    latest().emit('close')
    vi.advanceTimersByTime(BASE_RECONNECT_DELAY_MS - 1)
    expect(FakeWebSocket.instances).toHaveLength(2)
    vi.advanceTimersByTime(1)
    expect(FakeWebSocket.instances).toHaveLength(3)
  })

  it('keeps backing off when the socket drops before the stability window (flip-flop)', () => {
    new NotificationWebsocket()

    // Accept-then-immediate-drop: the first reconnect still uses the base delay.
    latest().emit('open')
    latest().emit('close')
    vi.advanceTimersByTime(BASE_RECONNECT_DELAY_MS)
    expect(FakeWebSocket.instances).toHaveLength(2)

    // The second flip-flop never reached the stability window, so the counter
    // is NOT reset: the delay doubles instead of hammering the endpoint at ~1/s.
    latest().emit('open')
    latest().emit('close')
    vi.advanceTimersByTime(BASE_RECONNECT_DELAY_MS)
    expect(FakeWebSocket.instances).toHaveLength(2)
    vi.advanceTimersByTime(BASE_RECONNECT_DELAY_MS)
    expect(FakeWebSocket.instances).toHaveLength(3)
  })

  it('re-attaches message handlers to the reconnected socket and ignores the dead one', () => {
    const ws = new NotificationWebsocket()
    const handler = vi.fn()
    ws.onMessage(handler)

    const dead = latest()
    dead.emit('close')
    vi.advanceTimersByTime(BASE_RECONNECT_DELAY_MS)
    const fresh = latest()
    expect(fresh).not.toBe(dead)

    fresh.emit('message', { data: JSON.stringify({ id: 'x', type: 'new' }) })
    expect(handler).toHaveBeenCalledWith({ id: 'x', type: 'new' })

    // A late message from the superseded socket must not be re-dispatched.
    handler.mockClear()
    dead.emit('message', { data: JSON.stringify({ id: 'y', type: 'new' }) })
    expect(handler).not.toHaveBeenCalled()
  })

  it('does not reconnect after an intentional close()', () => {
    const ws = new NotificationWebsocket()
    ws.close()
    latest().emit('close')
    vi.advanceTimersByTime(MAX_RECONNECT_DELAY_MS * 2)
    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it('clears a pending reconnect timer on close()', () => {
    const ws = new NotificationWebsocket()
    latest().emit('close')
    ws.close()
    vi.advanceTimersByTime(MAX_RECONNECT_DELAY_MS * 2)
    expect(FakeWebSocket.instances).toHaveLength(1)
  })
})
