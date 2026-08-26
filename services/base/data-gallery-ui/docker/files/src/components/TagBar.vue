<template>
  <!--  edit Mode-->
  <v-row v-if="editMode" dense align="center">
    <v-col cols="1" align="center">
      <v-icon>mdi-tag-outline</v-icon>
    </v-col>
    <v-col cols="7" style="padding-top: 8px; padding-bottom: 11px">
      <v-combobox
        label="Tags"
        v-model="tags"
        :items="availableTags"
        chips
        clearable
        multiple
        single-line
        closable-chips
        flat
        hide-details
        density="compact"
        variant="underlined"
        :disabled="disabledTagBar"
      >
        <template v-slot:chip="{ props: chipProps, item }">
          <v-chip v-bind="chipProps" variant="flat" :color="stringToColour(item.raw)" />
        </template>
      </v-combobox>
    </v-col>
    <v-col cols="1" align="center">
      <v-btn
        @click="editMode = !editMode"
        size="small"
        icon
        variant="text"
        :disabled="tags.length === 0 || disabledTagBar"
      >
        <v-icon>mdi-content-save</v-icon>
      </v-btn>
    </v-col>
    <v-col cols="3" align="center" justify="center">
      <v-switch
        v-model="multiple"
        label="Multiple Tags"
        density="compact"
        hide-details
        style="margin-top: 0"
        :disabled="disabledTagBar"
      ></v-switch>
    </v-col>
  </v-row>
  <!--  Tagging Mode-->
  <v-row v-else dense align="center">
    <v-col cols="1" align="center">
      <v-icon>mdi-tag-outline</v-icon>
    </v-col>
    <v-col cols="7" align="center">
      <v-chip-group
        v-model="selection"
        filter
        :multiple="multiple"
        @update:model-value="onChangeSelection"
        :disabled="disabledTagBar"
      >
        <!-- base-color: inside a group, VChip only applies `color` while selected -->
        <v-chip
          v-for="tag in tags"
          :key="tag"
          size="small"
          variant="flat"
          :base-color="stringToColour(tag)"
          :disabled="disabledTagBar"
        >
          {{ tag }}
        </v-chip>
      </v-chip-group>
    </v-col>
    <v-col cols="1" align="center">
      <v-btn @click="editMode = !editMode" size="small" icon variant="text" :disabled="disabledTagBar">
        <v-icon>mdi-application-edit-outline</v-icon>
      </v-btn>
    </v-col>
    <v-spacer></v-spacer>
    <v-col cols="3" align="center">
      <v-switch
        v-model="multiple"
        label="Multiple Tags"
        density="compact"
        hide-details
        style="margin-top: 0"
        :disabled="disabledTagBar"
      ></v-switch>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { loadValues } from '@/common/api.service'
import { stringToColour } from '@/utils/utils'
import { readSettings, settings as defaultSettings } from '@/static/defaultUIConfig'
import { useDatasetsStore } from '@/stores/datasets'

const datasets = useDatasetsStore()

const selection = ref<any>(null)
const editMode = ref(true)
const availableTags = ref<string[]>([])
const multiple = ref<boolean>(defaultSettings.datasets.tagBar.multiple)
const tags = ref<string[]>(defaultSettings.datasets.tagBar.tags)
const settings = ref<any>(defaultSettings)

function onChangeSelection() {
  if (multiple.value) {
    datasets.setActiveTags((selection.value as number[]).map((i) => tags.value[i]) || [])
  } else {
    datasets.setActiveTags(
      selection.value !== undefined && selection.value !== null
        ? [tags.value[selection.value as number]]
        : [],
    )
  }
}

function keypressListener(e: KeyboardEvent) {
  const keyCode = String.fromCharCode(e.keyCode)
  if (editMode.value || !Number.isInteger(Number(keyCode))) return
  const n = parseInt(keyCode) - 1
  if (n >= 0 && n < tags.value.length) {
    if (multiple.value) {
      const sel = selection.value as number[]
      if (sel.filter((t) => t === n).length > 0) {
        selection.value = sel.filter((t) => t !== n)
      } else {
        sel.push(n)
      }
      datasets.setActiveTags((selection.value as number[]).map((i) => tags.value[i]) || [])
    } else {
      selection.value = n
      datasets.setActiveTags(
        selection.value !== undefined && selection.value !== null
          ? [tags.value[selection.value as number]]
          : [],
      )
    }
  }
}

const disabledTagBar = computed(
  () =>
    !settings.value.datasets.cardText ||
    datasets.multiSelectKeyPressed ||
    datasets.selectedItems.length > 1,
)

watch(multiple, () => {
  selection.value = multiple.value ? [] : null
  const s = readSettings()
  s.datasets.tagBar.multiple = multiple.value
  localStorage['settings'] = JSON.stringify(s)
})

watch(tags, () => {
  const s = readSettings()
  s.datasets.tagBar.tags = tags.value
  localStorage['settings'] = JSON.stringify(s)
  onChangeSelection()
})

onMounted(() => {
  settings.value = readSettings()
  multiple.value = settings.value.datasets.tagBar.multiple
  tags.value = settings.value.datasets.tagBar.tags

  if (settings.value.datasets.tagBar.tags.length > 0) editMode.value = false

  loadValues('Tags')
    .then(
      (res) =>
        (availableTags.value =
          'items' in res.data ? res.data['items'].map((i: any) => i['value']) : []),
    )
    // loadValues already reported; the tag suggestions just stay empty.
    .catch(() => {})

  window.addEventListener('keypress', keypressListener)
})

onBeforeUnmount(() => {
  window.removeEventListener('keypress', keypressListener)
  datasets.setActiveTags([])
})
</script>

<style scoped></style>
