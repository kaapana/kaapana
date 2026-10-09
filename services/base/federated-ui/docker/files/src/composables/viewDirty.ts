import { computed, reactive, watch } from 'vue'
import { postViewDirty } from '@kaapana/base-ui'

const dirtySources = reactive(new Set<string>())

export const viewDirty = computed(() => dirtySources.size > 0)

watch(viewDirty, (dirty) => postViewDirty(dirty))

export function setDirty(source: string, dirty: boolean) {
  if (dirty) dirtySources.add(source)
  else dirtySources.delete(source)
}

export function clearDirty() {
  dirtySources.clear()
  postViewDirty(false)
}
