import { onBeforeUnmount, watch, type Ref } from 'vue'
import { postViewDirty } from '@kaapana/base-ui'

// The shell keeps one dirty flag per view, so publish the OR of all sections.
const reports = new Map<symbol, boolean>()

function publish() {
  postViewDirty([...reports.values()].some(Boolean))
}

export function useViewDirty(dirty: Ref<boolean>) {
  const key = Symbol('view-dirty')
  watch(
    dirty,
    (value) => {
      reports.set(key, value)
      publish()
    },
    { immediate: true },
  )
  onBeforeUnmount(() => {
    reports.delete(key)
    publish()
  })
}
