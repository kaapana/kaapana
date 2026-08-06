<template>
  <div align="right" :class="{ 'pagination-container': true, hidden: !showPagination }">
    <v-pagination v-if="showPagination" :length="computedLength" v-model="pageIndex"> </v-pagination>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    aggregatedSeriesNum: number
    pageLength?: number
    executeSlicedSearch?: boolean
  }>(),
  {
    pageLength: 1000,
    executeSlicedSearch: false,
  },
)

const emit = defineEmits<{
  onPageIndexChange: [pageIndex: number]
  updateData: [query: Record<string, unknown>, useLastQuery: boolean]
}>()

const pageIndex = ref(1)
const showPagination = ref(true)
let lastPage = 0
let lastPageLength = 0
const max_slices_per_pit = 1024 // Opensearch max_slices_per_pit default

const computedLength = computed(() => {
  const length = Math.ceil(props.aggregatedSeriesNum / props.pageLength)
  if (props.executeSlicedSearch && length > max_slices_per_pit) {
    return max_slices_per_pit
  }
  return length
})

function onPaginate() {
  if (pageIndex.value != lastPage || props.pageLength != lastPageLength) {
    emit('updateData', {}, true)
  }
  lastPage = pageIndex.value
  lastPageLength = props.pageLength
}

function updatePaginationVisibility() {
  showPagination.value = Math.ceil(props.aggregatedSeriesNum / props.pageLength) > 1
}

watch(
  () => props.pageLength,
  () => {
    updatePaginationVisibility()
    onPaginate()
  },
)

watch(
  () => props.aggregatedSeriesNum,
  () => {
    updatePaginationVisibility()
    if (pageIndex.value * props.pageLength > props.aggregatedSeriesNum) {
      pageIndex.value = 1
    }
  },
)

watch(pageIndex, () => {
  emit('onPageIndexChange', pageIndex.value)
  updatePaginationVisibility()
  onPaginate()
})

updatePaginationVisibility()
</script>

<style scoped>
.pagination-container {
  display: flex;
  flex-direction: column;
  align-items: left;
  margin-right: 10px;
  padding: 0;
}

.pagination-container.hidden {
  display: none;
}

.v-pagination {
  padding: 0;
  margin: 0;
  height: auto;
  width: auto;
}
</style>
