<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2">mdi-chart-areaspline</v-icon>
      Utilization
    </v-card-title>
    <v-card-text>
      <v-skeleton-loader v-if="!metrics.sampled" type="image" height="120" />
      <div v-else-if="metrics.allUnavailable" class="text-medium-emphasis">
        Monitoring data not available
      </div>
      <v-row v-else dense>
        <!-- 2-up. Vuetify breakpoints track the viewport, not this card, so a
             one-per-tile row would size itself as if the card were full width
             and wrap "3.2 MB/s" onto three lines in a third-width column.
             An odd last tile spans the row rather than leaving a dead half —
             GPU drops out entirely on platforms without gpu_support. -->
        <v-col
          v-for="(tile, i) in tiles"
          :key="tile.key"
          :cols="tiles.length % 2 && i === tiles.length - 1 ? 12 : 6"
        >
          <MetricTile
            :label="tile.label"
            :icon="tile.icon"
            :unit="tile.unit"
            :value="metrics[tile.key].current"
            :history="metrics[tile.key].history"
          />
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import MetricTile from '@/components/MetricTile.vue'
import { useMetricsStore, type MetricKey } from '@/stores/metrics'

const metrics = useMetricsStore()

interface Tile {
  key: MetricKey
  label: string
  icon: string
  unit: 'percent' | 'bytesPerSecond'
}

const allTiles: Tile[] = [
  { key: 'cpu', label: 'CPU', icon: 'mdi-cpu-64-bit', unit: 'percent' },
  { key: 'mem', label: 'Memory', icon: 'mdi-memory', unit: 'percent' },
  { key: 'net', label: 'Network', icon: 'mdi-lan', unit: 'bytesPerSecond' },
  { key: 'gpu', label: 'GPU', icon: 'mdi-expansion-card', unit: 'percent' },
]

// A GPU scrape job only exists on gpu_support platforms; hide the tile instead
// of showing a permanently empty gauge. Every metric stays visible on a failed
// request so a transient monitoring hiccup doesn't reshuffle the layout.
const tiles = computed(() => allTiles.filter((t) => t.key !== 'gpu' || !metrics.gpuAbsent))

onMounted(() => metrics.start())
onUnmounted(() => metrics.stop())
</script>
