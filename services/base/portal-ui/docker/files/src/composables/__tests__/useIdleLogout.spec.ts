import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/auth', () => ({ fetchUserinfo: vi.fn(), logout: vi.fn() }))

import { logout } from '@/api/auth'
import { useIdleLogout } from '@/composables/useIdleLogout'

const IDLE_TIMEOUT = parseInt(import.meta.env.VITE_APP_IDLE_TIMEOUT || '1800000', 10)

// One module-level timer; every test re-arms it through start().
describe('useIdleLogout', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    vi.mocked(logout).mockClear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('logs out once the idle timeout passes without activity', () => {
    useIdleLogout().start()
    vi.advanceTimersByTime(IDLE_TIMEOUT - 1)
    expect(logout).not.toHaveBeenCalled()
    vi.advanceTimersByTime(1)
    expect(logout).toHaveBeenCalledTimes(1)
  })

  it('restarts the countdown on activity in the shell window', () => {
    useIdleLogout().start()
    vi.advanceTimersByTime(IDLE_TIMEOUT - 1000)
    window.dispatchEvent(new Event('mousemove'))
    vi.advanceTimersByTime(1000)
    expect(logout).not.toHaveBeenCalled()
    vi.advanceTimersByTime(IDLE_TIMEOUT - 1000)
    expect(logout).toHaveBeenCalledTimes(1)
  })

  it('counts activity inside an attached iframe document as well', () => {
    const idle = useIdleLogout()
    idle.start()
    // Stands in for the embedded view's document, which IframeHost attaches on
    // every load because in-iframe activity never reaches the parent window.
    const viewDocument = document.implementation.createHTMLDocument('view')
    idle.attachActivityListeners(viewDocument)

    vi.advanceTimersByTime(IDLE_TIMEOUT - 1000)
    viewDocument.dispatchEvent(new Event('keydown'))
    vi.advanceTimersByTime(1000)
    expect(logout).not.toHaveBeenCalled()
    vi.advanceTimersByTime(IDLE_TIMEOUT - 1000)
    expect(logout).toHaveBeenCalledTimes(1)
  })
})
