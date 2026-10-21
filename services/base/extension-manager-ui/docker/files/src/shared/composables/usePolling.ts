import { onBeforeUnmount, watch, type Ref } from 'vue'

export function usePolling(task: () => Promise<unknown>, active: Ref<boolean>, intervalMs = 5000) {
  let timer: ReturnType<typeof setInterval> | undefined
  let running = false

  async function tick() {
    if (running) return
    running = true
    try {
      await task()
    } finally {
      running = false
    }
  }

  function stop() {
    if (timer !== undefined) clearInterval(timer)
    timer = undefined
  }

  watch(
    active,
    (isActive) => {
      if (isActive && timer === undefined) timer = setInterval(tick, intervalMs)
      if (!isActive) stop()
    },
    { immediate: true },
  )

  onBeforeUnmount(stop)
}
