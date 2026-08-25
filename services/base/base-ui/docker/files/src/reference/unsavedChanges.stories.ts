import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { computed, defineComponent, h, reactive, ref } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import {
  VAlert, VBtn, VCard, VCardActions, VCardText, VCardTitle, VChip, VDialog, VDivider, VSelect,
  VSpacer, VTextField, VTooltip,
} from 'vuetify/components'
import { postViewDirty } from '../utils/viewDirty'
import { note } from './storyNote'

// Two rules are in play and they are easy to conflate.
//
// The first is *when* to warn: only when the draft differs from what was saved.
// The mock below keeps a saved record per project, so "dirty" is a real
// comparison rather than "a field has content" — a pre-filled form the user never
// touched must not block navigation.
//
// The second is *who* warns. The view reports its state with `postViewDirty()` —
// that call is real — and the shell is what actually blocks a project switch,
// because in an embedded view only the shell sees the navigation. The dialog here
// stands in for the shell so the sequence is visible in one place; a view must
// not implement its own.
type ProjectId = 'project-a' | 'project-b'

interface Dataset {
  name: string
  modality: string
}

const MODALITIES = ['CT', 'MR', 'PT', 'US']

const projectNames: Record<ProjectId, string> = {
  'project-a': 'Project A',
  'project-b': 'Project B',
}

const UnsavedChanges = defineComponent({
  name: 'UnsavedChanges',
  setup() {
    // The saved records. Switching projects reads from here; Save writes to it.
    const saved = reactive<Record<ProjectId, Dataset>>({
      'project-a': { name: 'Lung Segmentation', modality: 'CT' },
      'project-b': { name: 'Brain Atlas', modality: 'MR' },
    })

    const current = ref<ProjectId>('project-a')
    const draft = reactive<Dataset>({ ...saved['project-a'] })
    const pending = ref<ProjectId | null>(null)

    const dirty = computed(
      () =>
        draft.name !== saved[current.value].name ||
        draft.modality !== saved[current.value].modality,
    )

    function touch() {
      postViewDirty(dirty.value)
    }

    function load(id: ProjectId) {
      current.value = id
      Object.assign(draft, saved[id])
      postViewDirty(false)
    }

    function save() {
      saved[current.value] = { ...draft }
      postViewDirty(false)
      notify({ type: 'success', title: `Saved to ${projectNames[current.value]}` })
    }

    // A switch is only interrupted when there is something to lose.
    function requestSwitch(id: ProjectId) {
      if (id === current.value) return
      postViewDirty(dirty.value)
      if (!dirty.value) {
        load(id)
        return
      }
      pending.value = id
    }

    function resolve(discard: boolean) {
      const target = pending.value
      pending.value = null
      if (discard && target) load(target)
    }

    return () =>
      h('div', [
        note(
          'Warn before navigation only when current data differs from saved data. Switching projects ' +
            'without edits proceeds immediately; editing a field first triggers the confirmation. ' +
            'Saving establishes a new unchanged state.',
        ),
        h(VCard, null, {
          default: () => [
            h(VCardTitle, null, {
              default: () => [
                'Editing in ',
                h(VChip, { color: 'primary', size: 'small', class: 'ml-1' }, {
                  default: () => projectNames[current.value],
                }),
              ],
            }),
            h(VCardText, null, {
              default: () => [
                h('div', { class: 'd-flex ga-2 align-center mb-4' }, [
                  h('span', { class: 'text-body-2 text-medium-emphasis' }, 'Project:'),
                  ...(Object.keys(projectNames) as ProjectId[]).map((id) =>
                    h(VBtn, {
                      key: id,
                      size: 'small',
                      color: id === current.value ? 'primary' : undefined,
                      variant: id === current.value ? 'flat' : 'outlined',
                      onClick: () => requestSwitch(id),
                    }, { default: () => projectNames[id] }),
                  ),
                ]),
                h(VTextField, {
                  label: 'Dataset name',
                  modelValue: draft.name,
                  'onUpdate:modelValue': (v: string) => {
                    draft.name = v
                    touch()
                  },
                }),
                h(VSelect, {
                  label: 'Modality',
                  items: MODALITIES,
                  modelValue: draft.modality,
                  'onUpdate:modelValue': (v: string) => {
                    draft.modality = v
                    touch()
                  },
                }),
                h(VAlert, {
                  type: dirty.value ? 'warning' : 'success',
                  variant: 'tonal',
                  density: 'compact',
                }, {
                  default: () =>
                    dirty.value
                      ? 'Unsaved changes — the view has reported itself dirty to the shell.'
                      : 'No changes — navigation is not blocked.',
                }),
                h(VDivider, { class: 'my-4' }),
                // Showing both saved records makes "it was actually saved" checkable
                // rather than a claim.
                h('div', { class: 'text-caption text-medium-emphasis' }, [
                  h('div', { class: 'mb-1' }, 'Saved records:'),
                  ...(Object.keys(projectNames) as ProjectId[]).map((id) =>
                    h('div', { key: id }, `${projectNames[id]}: ${saved[id].name} · ${saved[id].modality}`),
                  ),
                ]),
              ],
            }),
            h(VCardActions, null, {
              default: () => [
                h(VSpacer),
                // Save is unavailable with nothing to save, and says so — the same
                // rule the Buttons page states. A disabled control with no
                // explanation is a dead end, including this one.
                dirty.value
                  ? h(VBtn, { color: 'primary', onClick: save }, { default: () => 'Save' })
                  : h(VTooltip, { location: 'top', text: 'No changes to save.' }, {
                      activator: ({ props }: { props: Record<string, unknown> }) =>
                        h('span', props, [
                          h(VBtn, { color: 'primary', disabled: true }, { default: () => 'Save' }),
                        ]),
                    }),
              ],
            }),
          ],
        }),
        h(
          VDialog,
          {
            modelValue: pending.value !== null,
            maxWidth: 400,
            // Dismissing is the safe answer: stay here and keep the edit.
            'onUpdate:modelValue': (value: boolean) => {
              if (!value) resolve(false)
            },
          },
          {
            default: () =>
              h(VCard, null, {
                default: () => [
                  h(VCardTitle, null, { default: () => 'Leave without saving?' }),
                  h(VCardText, null, {
                    default: () =>
                      pending.value
                        ? `Switching to ${projectNames[pending.value]} reloads this view. ` +
                          `Your unsaved changes to "${saved[current.value].name}" will be lost.`
                        : '',
                  }),
                  h(VCardActions, null, {
                    default: () => [
                      h(VSpacer),
                      h(VBtn, { autofocus: true, onClick: () => resolve(false) }, {
                        default: () => 'Keep editing',
                      }),
                      h(VBtn, { color: 'error', onClick: () => resolve(true) }, {
                        default: () => 'Discard changes',
                      }),
                    ],
                  }),
                ],
              }),
          },
        ),
      ])
  },
})

const meta: Meta<typeof UnsavedChanges> = {
  title: 'Guidelines / Patterns / Unsaved Changes',
  component: UnsavedChanges,
}

export default meta
type Story = StoryObj<typeof UnsavedChanges>

export const Default: Story = {}
