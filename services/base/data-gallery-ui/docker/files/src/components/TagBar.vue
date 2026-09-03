<template>
  <!--  Edit mode -->
  <v-row v-if="editMode" dense align="center">
    <v-col cols="1" align="center">
      <v-icon :icon="galleryIcons.tag" />
    </v-col>
    <v-col cols="7" class="py-2">
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
          <v-chip v-bind="chipProps" variant="flat" :style="chipStyle(item.raw)" />
        </template>
      </v-combobox>
    </v-col>
    <v-col cols="1" align="center">
      <v-tooltip location="bottom" :text="editToggleHint">
        <template v-slot:activator="{ props: activator }">
          <span v-bind="activator">
            <v-btn
              size="small"
              variant="text"
              :icon="kaapanaIcons.save"
              aria-label="Save tag list"
              :disabled="tags.length === 0 || disabledTagBar"
              @click="editMode = !editMode"
            />
          </span>
        </template>
      </v-tooltip>
    </v-col>
    <v-col cols="3" align="center" justify="center">
      <v-switch
        v-model="multiple"
        label="Multiple Tags"
        density="compact"
        hide-details
        class="mt-0"
        :disabled="disabledTagBar"
      ></v-switch>
    </v-col>
  </v-row>
  <!--  Tagging mode -->
  <v-row v-else dense align="center">
    <v-col cols="1" align="center">
      <v-icon :icon="galleryIcons.tag" />
    </v-col>
    <v-col cols="7" align="center">
      <v-chip-group
        v-model="selection"
        filter
        :multiple="multiple"
        @update:model-value="onChangeSelection"
        :disabled="disabledTagBar"
      >
        <!-- base-color: inside a group, VChip only applies `color` while
             selected. The foreground is set alongside it, because Vuetify
             derives a contrasting one only for theme tokens, not a literal
             hex. -->
        <v-chip
          v-for="tag in tags"
          :key="tag"
          size="small"
          variant="flat"
          :base-color="tagColor(tag).background"
          :style="{ color: tagColor(tag).text }"
          :disabled="disabledTagBar"
        >
          {{ tag }}
        </v-chip>
      </v-chip-group>
    </v-col>
    <v-col cols="1" align="center">
      <v-tooltip location="bottom" :text="editToggleHint">
        <template v-slot:activator="{ props: activator }">
          <span v-bind="activator">
            <v-btn
              size="small"
              variant="text"
              :icon="kaapanaIcons.edit"
              aria-label="Edit tag list"
              :disabled="disabledTagBar"
              @click="editMode = !editMode"
            />
          </span>
        </template>
      </v-tooltip>
    </v-col>
    <v-spacer></v-spacer>
    <v-col cols="3" align="center">
      <v-switch
        v-model="multiple"
        label="Multiple Tags"
        density="compact"
        hide-details
        class="mt-0"
        :disabled="disabledTagBar"
      ></v-switch>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { loadValues } from '@/common/api.service'
import { tagColor } from '@/utils/tagColors'
import { kaapanaIcons, galleryIcons } from '@/utils/galleryIcons'
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

// A disabled control explains why it is unavailable when the reason is not
// obvious (guidelines, "Unavailable actions"). Tagging acts on one card at a
// time, so it is off while a multi-selection is active.
const editToggleHint = computed(() => {
  if (!settings.value.datasets.cardText) return 'Tagging needs card text enabled in the settings'
  if (datasets.multiSelectKeyPressed || datasets.selectedItems.length > 1) {
    return 'Tagging applies to a single series — clear the multi-selection first'
  }
  return editMode.value ? 'Save tag list' : 'Edit tag list'
})

function chipStyle(tag: string) {
  const { background, text } = tagColor(tag)
  return { backgroundColor: background, color: text }
}

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
