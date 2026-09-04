import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/notifications', () => ({
  fetchNotifications: vi.fn(),
  readNotification: vi.fn(),
  readAllNotifications: vi.fn(),
  NotificationWebsocket: class {},
  NotificationEventType: { NEW: 'new', READ: 'read', READ_ALL: 'read_all' },
}))

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
