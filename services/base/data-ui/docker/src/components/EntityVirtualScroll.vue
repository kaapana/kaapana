        <script setup lang="ts">
        import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
        import { useDisplay } from 'vuetify'
        import EntityCard from '@/components/EntityCard.vue'
        import type { GalleryItem } from '@/types/domain'

        const props = withDefaults(
          defineProps<{
            length: number
            resolveItem: (index: number) => { id: string; card: GalleryItem | null }
            height?: string | number
            itemHeight?: number
            columnsOverride?: number | null
          }>(),
          {
            height: '100%',
            itemHeight: 520,
            columnsOverride: null,
          },
        )

        const emit = defineEmits<{
          (e: 'view', id: string): void
          (e: 'delete', id: string): void
          (e: 'need-range', payload: { start: number; end: number }): void
        }>()

        const display = useDisplay()

        type VirtualScrollInstance = {
          $el: HTMLElement | null
          scrollToIndex: (index: number) => void
        }

        const virtualScrollRef = ref<VirtualScrollInstance | null>(null)
        const scrollElement = ref<HTMLElement | null>(null)
        const indicatorValue = ref(1)
        const chipVisible = ref(false)
        const chipTop = ref('0%')
        const pointerNearScrollbar = ref(false)
        const pointerDragging = ref(false)

        const HOVER_ZONE_PX = 36
        const BOTTOM_STICKY_THRESHOLD_PX = 48
        let hideChipTimeout: ReturnType<typeof window.setTimeout> | null = null
        let activePointerId: number | null = null
        const stickToBottom = ref(true)

        const columns = computed(() => {
          const override = props.columnsOverride
          if (override && override > 0) {
            return Math.max(1, Math.floor(override))
          }
          if (display.xlAndUp.value) {
            return 3
          }
          if (display.mdAndUp.value) {
            return 2
          }
          return 1
        })

        const rowGridTemplateStyle = computed(() => ({
          gridTemplateColumns: `repeat(${columns.value}, minmax(0, 1fr))`,
        }))

        interface RowChunk {
          start: number
          cells: Array<{ id: string; card: GalleryItem | null }>
        }

        function getRowCells(rowIndex: number) {
          const size = columns.value
          const start = rowIndex * size
          const cells: Array<{ id: string; card: GalleryItem | null }> = []
          for (let offset = 0; offset < size; offset += 1) {
            const index = start + offset
            if (index >= props.length) {
              break
            }
            cells.push(props.resolveItem(index))
          }
          return { start, cells }
        }

        function rowNeedsData(row: RowChunk): boolean {
          return row.cells.some((cell) => !cell.card)
        }

        function handleRowIntersect(rowIndex: number, isIntersecting: boolean) {
          if (!isIntersecting) {
            return
          }
          const row = getRowCells(rowIndex)
          if (rowNeedsData(row)) {
            const rowEnd = row.start + row.cells.length - 1
            emit('need-range', { start: row.start, end: rowEnd })
          }
        }

        function createRowObserver(rowIndex: number) {
          return (isIntersecting: boolean) => handleRowIntersect(rowIndex, isIntersecting)
        }

        const rowCount = computed(() => {
          if (!props.length) {
            return 0
          }
          return Math.ceil(props.length / columns.value)
        })

        const rowIndices = computed(() => {
          return Array.from({ length: rowCount.value }, (_, index) => index)
        })

        const emptyHeightStyle = computed(() => {
          return typeof props.height === 'number' ? `${props.height}px` : props.height
        })

        const enableChip = computed(() => props.length > columns.value)
        const chipLabel = computed(() => `#${indicatorValue.value}`)
        const showChipIndicator = computed(() => enableChip.value && chipVisible.value)

        function clampRowIndex(index: number) {
          if (!rowCount.value) {
            return 0
          }
          return Math.min(Math.max(index, 0), rowCount.value - 1)
        }

        function clampEntityIndex(index: number) {
          if (!props.length) {
            return 1
          }
          return Math.min(Math.max(index, 1), props.length)
        }

        function scrollToRow(rowIndex: number) {
          const target = clampRowIndex(rowIndex)
          virtualScrollRef.value?.scrollToIndex(target)
        }

        function scrollToEntityIndex(index: number) {
          const safeIndex = clampEntityIndex(index)
          const rowIndex = Math.floor((safeIndex - 1) / columns.value)
          scrollToRow(rowIndex)
        }

        function entityIndexFromRatio(ratio: number) {
          if (!props.length) {
            return 1
          }
          const total = props.length
          const clamped = Math.min(Math.max(ratio, 0), 1)
          return clampEntityIndex(Math.round(clamped * (total - 1)) + 1)
        }

        function updateBottomStickiness() {
          const element = scrollElement.value
          if (!element) {
            stickToBottom.value = true
            return
          }
          const distanceFromBottom = element.scrollHeight - (element.scrollTop + element.clientHeight)
          stickToBottom.value = distanceFromBottom <= BOTTOM_STICKY_THRESHOLD_PX
        }

        function updateChipFromScroll() {
          if (!scrollElement.value || !enableChip.value) {
            return
          }
          const scrollable = scrollElement.value.scrollHeight - scrollElement.value.clientHeight
          const ratio = scrollable <= 0 ? 0 : scrollElement.value.scrollTop / scrollable
          if (!pointerNearScrollbar.value && !pointerDragging.value) {
            chipTop.value = `${ratio * 100}%`
          }
          chipVisible.value = true
          scheduleChipHide()
        }

        function syncIndicatorToScroll() {
          if (!scrollElement.value) {
            return
          }
          const rowHeight = Number(props.itemHeight) || 1
          const scrollTop = scrollElement.value.scrollTop
          const rowIndex = clampRowIndex(Math.floor(scrollTop / rowHeight))
          const entityIndex = rowIndex * columns.value + 1
          indicatorValue.value = clampEntityIndex(entityIndex)
          updateChipFromScroll()
          updateBottomStickiness()
        }

        function scheduleChipHide(delay = 1200) {
          if (!enableChip.value || pointerNearScrollbar.value || pointerDragging.value) {
            return
          }
          if (hideChipTimeout) {
            window.clearTimeout(hideChipTimeout)
          }
          hideChipTimeout = window.setTimeout(() => {
            if (!pointerNearScrollbar.value && !pointerDragging.value) {
              chipVisible.value = false
            }
          }, delay)
        }

        function cancelChipHide() {
          if (!hideChipTimeout) {
            return
          }
          window.clearTimeout(hideChipTimeout)
          hideChipTimeout = null
        }

        function handlePointerMove(event: PointerEvent) {
          if (!enableChip.value || !scrollElement.value) {
            return
          }
          const rect = scrollElement.value.getBoundingClientRect()
          const offsetFromRight = rect.right - event.clientX
          const nearScrollbar = offsetFromRight >= -4 && offsetFromRight <= HOVER_ZONE_PX
          pointerNearScrollbar.value = nearScrollbar
          if (!nearScrollbar && !pointerDragging.value) {
            scheduleChipHide()
            return
          }
          const ratio = (event.clientY - rect.top) / rect.height
          const clampedRatio = Math.min(Math.max(ratio, 0), 1)
          const targetIndex = entityIndexFromRatio(clampedRatio)
          indicatorValue.value = targetIndex
          chipTop.value = `${clampedRatio * 100}%`
          chipVisible.value = true
          cancelChipHide()
          if (pointerDragging.value) {
            scrollToEntityIndex(targetIndex)
          }
        }

        function finishPointerDrag(pointerId?: number) {
          if (!pointerDragging.value) {
            return
          }
          pointerDragging.value = false
          if (pointerId !== undefined && scrollElement.value?.hasPointerCapture?.(pointerId)) {
            scrollElement.value.releasePointerCapture(pointerId)
          }
          window.removeEventListener('pointerup', handleWindowPointerUp)
          activePointerId = null
          if (!pointerNearScrollbar.value) {
            scheduleChipHide()
            syncIndicatorToScroll()
          }
        }

        function handlePointerDown(event: PointerEvent) {
          if (!enableChip.value) {
            return
          }
          handlePointerMove(event)
          if (!pointerNearScrollbar.value) {
            return
          }
          pointerDragging.value = true
          activePointerId = event.pointerId
          scrollElement.value?.setPointerCapture?.(event.pointerId)
          window.addEventListener('pointerup', handleWindowPointerUp)
          scrollToEntityIndex(indicatorValue.value)
        }

        function handlePointerLeave() {
          pointerNearScrollbar.value = false
          if (!pointerDragging.value) {
            scheduleChipHide()
            syncIndicatorToScroll()
          }
        }

        function handlePointerUp(event: PointerEvent) {
          if (activePointerId !== event.pointerId) {
            return
          }
          finishPointerDrag(event.pointerId)
        }

        function handleWindowPointerUp(event: PointerEvent) {
          if (activePointerId !== event.pointerId) {
            return
          }
          finishPointerDrag(event.pointerId)
        }

        function detachListeners(el: HTMLElement | null) {
          if (!el) {
            return
          }
          el.removeEventListener('scroll', syncIndicatorToScroll)
          el.removeEventListener('pointermove', handlePointerMove)
          el.removeEventListener('pointerdown', handlePointerDown)
          el.removeEventListener('pointerleave', handlePointerLeave)
          el.removeEventListener('pointerup', handlePointerUp)
        }

        function attachScrollListener(el: HTMLElement | null) {
          if (scrollElement.value) {
            detachListeners(scrollElement.value)
          }
          scrollElement.value = el
          if (el) {
            el.addEventListener('scroll', syncIndicatorToScroll, { passive: true })
            el.addEventListener('pointermove', handlePointerMove)
            el.addEventListener('pointerdown', handlePointerDown)
            el.addEventListener('pointerleave', handlePointerLeave)
            el.addEventListener('pointerup', handlePointerUp)
            syncIndicatorToScroll()
          } else {
            stickToBottom.value = true
          }
        }

        watch(
          () => props.length,
          (length, previousLength) => {
            if (!length) {
              indicatorValue.value = 1
              chipVisible.value = false
              stickToBottom.value = true
              return
            }
            indicatorValue.value = Math.min(indicatorValue.value, length)
            if (previousLength !== undefined && length > (previousLength ?? 0) && stickToBottom.value) {
              void nextTick(() => {
                scrollToEntityIndex(length)
              })
            }
          },
          { immediate: true },
        )

        watch(enableChip, (enabled) => {
          if (!enabled) {
            chipVisible.value = false
            pointerNearScrollbar.value = false
            finishPointerDrag()
            cancelChipHide()
          }
        })

        onMounted(() => {
          const element = (virtualScrollRef.value?.$el ?? null) as HTMLElement | null
          attachScrollListener(element)
        })

        watch(
          () => (virtualScrollRef.value?.$el ?? null) as HTMLElement | null,
          (element) => {
            attachScrollListener(element)
          },
        )

        onBeforeUnmount(() => {
          cancelChipHide()
          finishPointerDrag()
          stickToBottom.value = true
          attachScrollListener(null)
          window.removeEventListener('pointerup', handleWindowPointerUp)
        })
</script>

<template>
  <div class="entity-virtual-scroll">
    <div v-if="rowIndices.length" class="entity-virtual-scroll__body">
      <div class="entity-virtual-scroll__scroller-wrapper">
        <v-virtual-scroll
          ref="virtualScrollRef"
          class="entity-virtual-scroll__scroller"
          :height="height"
          :items="rowIndices"
          :item-height="itemHeight"
          :bench="6"
        >
          <template #default="{ item: rowIndex }">
            <template v-if="typeof rowIndex === 'number' && rowIndex < rowCount">
              <div
                v-for="row in [getRowCells(rowIndex)]"
                :key="`row-${rowIndex}`"
                class="entity-row"
                :style="rowGridTemplateStyle"
                v-intersect="createRowObserver(rowIndex)"
              >
                <div v-for="cell in row.cells" :key="cell.id" class="entity-cell">
                  <EntityCard
                    v-if="cell.card"
                    :item="cell.card"
                    @view="emit('view', $event)"
                    @delete="emit('delete', $event)"
                  />
                  <div v-else class="entity-card placeholder">
                    <v-skeleton-loader type="image, article, actions"></v-skeleton-loader>
                  </div>
                </div>
              </div>
            </template>
          </template>
        </v-virtual-scroll>

        <transition name="entity-virtual-scroll__chip-fade">
          <div
            v-if="showChipIndicator"
            class="entity-virtual-scroll__chip"
            :style="{ top: chipTop }"
          >
            {{ chipLabel }}
          </div>
        </transition>
      </div>
    </div>

    <div v-else class="entity-virtual-scroll__empty" :style="{ minHeight: emptyHeightStyle }">
      <slot name="empty"></slot>
    </div>

  </div>
</template>

<style scoped>
.entity-virtual-scroll {
  position: relative;
}

.entity-virtual-scroll__body {
  display: flex;
}

.entity-virtual-scroll__scroller-wrapper {
  position: relative;
  flex: 1;
}

.entity-virtual-scroll__scroller {
  border-radius: 12px;
  padding: 8px;
}

.entity-virtual-scroll__chip {
  position: absolute;
  right: 4px;
  transform: translateY(-50%);
  padding: 4px 10px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  box-shadow: var(--v-shadow-2);
  font-size: 0.75rem;
  pointer-events: none;
}

.entity-virtual-scroll__chip-fade-enter-active,
.entity-virtual-scroll__chip-fade-leave-active {
  transition: opacity 150ms ease;
}

.entity-virtual-scroll__chip-fade-enter-from,
.entity-virtual-scroll__chip-fade-leave-to {
  opacity: 0;
}

.entity-row {
  display: grid;
  gap: 16px;
  padding: 8px;
}

.entity-cell {
  display: flex;
}

.entity-cell :deep(.entity-card) {
  width: 100%;
}

.entity-virtual-scroll__empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.entity-card.placeholder {
  width: 100%;
  border-radius: 16px;
  overflow: hidden;
}
</style>
