import { useAuthStore } from '@/stores/auth'

// One module-level idle-logout timer shared by the whole shell so activity
// anywhere — including inside same-origin iframes — resets the same countdown.
// Activity inside an iframe never bubbles to the parent, so IframeHost attaches
// listeners to each iframe document on every "load".

const ACTIVITY_EVENTS = [
  'mousemove',
  'keydown',
  'mousedown',
  'touchstart',
  'scroll',
  'visibilitychange',
] as const

const IDLE_TIMEOUT = parseInt(import.meta.env.VITE_APP_IDLE_TIMEOUT || '1800000', 10)

let timer: ReturnType<typeof setTimeout> | null = null

function reset() {
  if (timer) clearTimeout(timer)
  // Deliberately not behind viewState.confirmLeave(): nobody is present to
  // answer, and a pending confirm would keep the session open indefinitely.
  timer = setTimeout(() => {
    useAuthStore().logout()
  }, IDLE_TIMEOUT)
}

function attachActivityListeners(target: Document | Window) {
  ACTIVITY_EVENTS.forEach((event) => {
    target.addEventListener(event, reset, { passive: true })
  })
}

export function useIdleLogout() {
  return {
    /** Start (or restart) the idle countdown and watch the shell window. */
    start() {
      attachActivityListeners(window)
      reset()
    },
    attachActivityListeners,
  }
}
