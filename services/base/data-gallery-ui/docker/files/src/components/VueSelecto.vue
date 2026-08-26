<template>
  <!-- Selecto manages its own selection-box overlay imperatively. -->
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import Selecto from 'selecto'

// Thin Vue 3 wrapper over the framework-agnostic `selecto` core, replacing the
// Vue 2-only `vue-selecto` package. Props/events mirror the subset the gallery
// used.
const props = withDefaults(
  defineProps<{
    dragContainer?: string
    selectableTargets?: string[]
    hitRate?: number
    selectByClick?: boolean
    selectFromInside?: boolean
    continueSelect?: boolean
    toggleContinueSelect?: string[] | string
    ratio?: number
  }>(),
  {
    hitRate: 100,
    selectByClick: true,
    selectFromInside: true,
    continueSelect: false,
    ratio: 0,
  },
)

const emit = defineEmits<{
  dragStart: [event: any]
  select: [event: any]
}>()

let selecto: Selecto | null = null

onMounted(() => {
  selecto = new Selecto({
    container: document.body,
    dragContainer: props.dragContainer,
    selectableTargets: props.selectableTargets,
    hitRate: props.hitRate,
    selectByClick: props.selectByClick,
    selectFromInside: props.selectFromInside,
    continueSelect: props.continueSelect,
    toggleContinueSelect: props.toggleContinueSelect,
    ratio: props.ratio,
  } as any)
  selecto.on('dragStart', (e: any) => emit('dragStart', e))
  selecto.on('select', (e: any) => emit('select', e))
})

onBeforeUnmount(() => {
  selecto?.destroy()
  selecto = null
})
</script>
