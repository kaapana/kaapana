import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// The socket's only role here is to hand the store's handler to the tests, so
// events can be delivered without a WebSocket.
type WsEvent = { type: string; notification_id?: string }
const ws = vi.hoisted(() => ({
  handler: null as ((event: WsEvent) => Promise<void> | void) | null,
}))

vi.mock('@/api/notifications', () => ({
  fetchNotifications: vi.fn(),
  readNotification: vi.fn(),
  readAllNotifications: vi.fn(),
  NotificationWebsocket: class {
    onMessage(handler: (event: WsEvent) => Promise<void> | void) {
      ws.handler = handler
    }
  },
  NotificationEventType: { NEW: 'new', READ: 'read', READ_ALL: 'read_all' },
}))

vi.mock('@kyvg/vue3-notification', () => ({ notify: vi.fn() }))

import { notify } from '@kyvg/vue3-notification'
import { useNotificationsStore } from '@/stores/notifications'
import {
  fetchNotifications,
  readNotification,
  readAllNotifications,
  type KaapanaNotification,
} from '@/api/notifications'

type FetchResult = Awaited<ReturnType<typeof fetchNotifications>>

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((r) => (resolve = r))
  return { promise, resolve }
}

const N = (id: string): KaapanaNotification => ({
  id,
  topic: 'Workflows',
  title: id,
  description: '',
  icon: '',
  link: '',
  timestamp: new Date('2026-01-01T00:00:00Z'),
})

const page = (ids: string[], meta: Partial<FetchResult['meta']> = {}): FetchResult => ({
  data: ids.map(N),
  meta: { nextCursor: null, hasMore: false, total: ids.length, ...meta },
})

describe('notifications store refresh race', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('drops a stale in-flight page when refresh restarts from the top', async () => {
    const store = useNotificationsStore()
    const stalePage2 = deferred<FetchResult>()
    const freshPage1 = deferred<FetchResult>()
    vi.mocked(fetchNotifications).mockImplementation((params) =>
      params?.cursor ? stalePage2.promise : freshPage1.promise,
    )

    // A scroll-triggered second-page fetch is in flight (the cursor has already
    // advanced past the top of the list).
    store.cursor = 'cursor-page-2'
    const scrollLoad = store.loadMore()
    expect(store.loading).toBe(true)

    // A websocket "new" event fires refresh() while that page is still pending.
    const refreshDone = store.refresh()
    // refresh() re-fetches from the top; its response lands first.
    freshPage1.resolve(page(['new-1', 'a', 'b'], { nextCursor: 'cursor-page-2', hasMore: true, total: 42 }))
    await refreshDone

    expect(store.notifications.map((n) => n.id)).toEqual(['new-1', 'a', 'b'])
    expect(store.loading).toBe(false)

    // The stale page-2 response only now resolves. It must be discarded rather
    // than pushed into the freshly refreshed list, and must not advance state.
    stalePage2.resolve(page(['old-1', 'old-2'], { nextCursor: 'cursor-page-3', hasMore: false, total: 7 }))
    await scrollLoad

    expect(store.notifications.map((n) => n.id)).toEqual(['new-1', 'a', 'b'])
    expect(store.notifications.some((n) => n.id.startsWith('old'))).toBe(false)
    expect(store.cursor).toBe('cursor-page-2')
    expect(store.total).toBe(42)
    // the guard is clean again, so a later scroll may load once more
    expect(store.loading).toBe(false)
  })

  it('keeps the guard held for the superseding refresh when a stale load resolves first', async () => {
    const store = useNotificationsStore()
    const stalePage2 = deferred<FetchResult>()
    const freshPage1 = deferred<FetchResult>()
    vi.mocked(fetchNotifications).mockImplementation((params) =>
      params?.cursor ? stalePage2.promise : freshPage1.promise,
    )

    store.cursor = 'cursor-page-2'
    const scrollLoad = store.loadMore()
    // refresh()'s own load starts and stays pending (freshPage1 unresolved).
    const refreshDone = store.refresh()

    // The stale page resolves first: it must be dropped AND must not release the
    // loading guard that the refresh's still-pending load now owns.
    stalePage2.resolve(page(['old-1'], { nextCursor: 'cursor-page-3', hasMore: false, total: 7 }))
    await scrollLoad
    expect(store.loading).toBe(true)
    expect(store.notifications).toEqual([])

    // The refresh's own load finishes: it commits and releases the guard.
    freshPage1.resolve(page(['new-1'], { nextCursor: null, hasMore: false, total: 1 }))
    await refreshDone
    expect(store.notifications.map((n) => n.id)).toEqual(['new-1'])
    expect(store.loading).toBe(false)
  })

  it('still guards against concurrent scroll loads', async () => {
    const store = useNotificationsStore()
    const first = deferred<FetchResult>()
    vi.mocked(fetchNotifications).mockReturnValueOnce(first.promise)

    const load = store.loadMore()
    expect(store.loading).toBe(true)
    // a second concurrent scroll load is swallowed while the first is in flight
    await store.loadMore()
    expect(vi.mocked(fetchNotifications)).toHaveBeenCalledTimes(1)

    first.resolve(page(['x']))
    await load
    expect(store.notifications.map((n) => n.id)).toEqual(['x'])
  })
})

describe('notifications store markAllAsRead', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('uses the bulk endpoint once, however many pages are unread', async () => {
    const store = useNotificationsStore()
    vi.mocked(fetchNotifications)
      .mockResolvedValueOnce(page(['a', 'b'], { nextCursor: 'cursor-page-2', hasMore: true, total: 40 }))
      .mockResolvedValue(page([]))
    await store.loadMore()

    await store.markAllAsRead()

    expect(readAllNotifications).toHaveBeenCalledTimes(1)
    expect(readNotification).not.toHaveBeenCalled()
    expect(store.notifications).toEqual([])
  })
})

describe('notifications store websocket events', () => {
  let store: ReturnType<typeof useNotificationsStore>

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
    vi.mocked(fetchNotifications).mockResolvedValue(page([]))
    store = useNotificationsStore()
    store.connect()
    // connect() kicks off its own refresh; settle it so the fetch counts below
    // only cover what the delivered event caused.
    await store.refresh()
    vi.mocked(fetchNotifications).mockClear()
  })

  it('applies a "read" event locally: drops the item, decrements the badge, no fetch', async () => {
    store.notifications = [N('a'), N('b')]
    store.total = 5

    await ws.handler!({ type: 'read', notification_id: 'a' })

    expect(store.notifications.map((n) => n.id)).toEqual(['b'])
    expect(store.total).toBe(4)
    expect(fetchNotifications).not.toHaveBeenCalled()
  })

  it('counts a "read" event for an id beyond the loaded pages, never below zero', async () => {
    store.notifications = [N('a')]
    store.total = 1

    await ws.handler!({ type: 'read', notification_id: 'page-2-item' })
    expect(store.notifications.map((n) => n.id)).toEqual(['a'])
    expect(store.total).toBe(0)

    await ws.handler!({ type: 'read', notification_id: 'page-3-item' })
    expect(store.total).toBe(0)
    expect(fetchNotifications).not.toHaveBeenCalled()
  })

  it('empties the list and zeroes the badge on "read_all" without fetching', async () => {
    store.notifications = [N('a'), N('b')]
    store.total = 2

    await ws.handler!({ type: 'read_all' })

    expect(store.notifications).toEqual([])
    expect(store.total).toBe(0)
    expect(fetchNotifications).not.toHaveBeenCalled()
  })

  it('refetches once on "new" and toasts the item named by notification_id', async () => {
    vi.mocked(fetchNotifications).mockResolvedValue(page(['n1']))

    await ws.handler!({ type: 'new', notification_id: 'n1' })

    expect(fetchNotifications).toHaveBeenCalledTimes(1)
    expect(notify).toHaveBeenCalledWith(expect.objectContaining({ title: 'n1' }))
  })

  it('clears locally after mark-all-as-read instead of refetching the list', async () => {
    store.notifications = [N('a'), N('b')]
    store.total = 2

    await store.markAllAsRead()

    expect(readAllNotifications).toHaveBeenCalledTimes(1)
    expect(store.notifications).toEqual([])
    expect(store.total).toBe(0)
    expect(fetchNotifications).not.toHaveBeenCalled()
  })
})
