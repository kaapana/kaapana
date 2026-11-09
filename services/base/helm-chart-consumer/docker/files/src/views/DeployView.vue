<template>
  <UnavailableState v-if="!mock.can.deploy" view="Deploying applications" />
  <v-container v-else class="text-left">
    <v-btn variant="text" prepend-icon="mdi-arrow-left" to="/catalog" class="mb-2 ml-n2"
      >Application Catalog</v-btn
    >

    <v-card v-if="!def" :elevation="2">
      <v-empty-state
        size="56"
        :title="`This application cannot be deployed in ${mock.project?.name}`"
        text="It is not enabled for this project. Kaapana system admins choose which applications each project can deploy."
      >
        <template #actions>
          <v-btn color="primary" variant="text" to="/catalog">Back to the catalog</v-btn>
        </template>
      </v-empty-state>
    </v-card>

    <v-card v-else-if="blocked" :elevation="2">
      <v-empty-state
        size="56"
        :title="`${def.name} is already deployed in ${mock.project?.name}`"
        :text="`It can be deployed once per project. The existing instance is ${blocked.name}.`"
      >
        <template #actions>
          <v-btn color="primary" variant="text" :to="`/applications/${blocked.name}`"
            >View {{ blocked.name }}</v-btn
          >
        </template>
      </v-empty-state>
    </v-card>

    <template v-else>
      <h1 class="text-h4">Deploy {{ def.name }} <StoryRef ids="2.1" /></h1>
      <p class="text-body-2 text-medium-emphasis mt-1 mb-4">
        Version {{ def.version }} · into {{ mock.project?.name }}
      </p>

      <v-form ref="formRef" @submit.prevent="submit">
        <v-row>
          <v-col cols="12" md="7" lg="8">
            <v-card :elevation="2" class="mb-4">
              <v-card-title>Instance</v-card-title>
              <v-card-text>
                <v-text-field
                  id="field-name"
                  v-model="form.name"
                  label="Name *"
                  :rules="nameRules"
                  hint="Unique in the project and part of the address."
                  persistent-hint
                  class="mb-2"
                >
                  <template #append><StoryRef ids="8.3" /></template>
                </v-text-field>
                <v-select
                  id="field-for"
                  v-model="form.forPerson"
                  :items="people"
                  label="For"
                  hint="The scientist who works in this instance. Every member of the project can still open it."
                  persistent-hint
                  class="mb-2"
                >
                  <template #append><StoryRef ids="2.1 Q1" /></template>
                </v-select>
                <v-textarea
                  id="field-description"
                  v-model="form.description"
                  label="Use case"
                  rows="2"
                  auto-grow
                  counter="200"
                  :rules="[descriptionRule]"
                  hint="Why this instance exists, so it is still clear in a few weeks."
                  persistent-hint
                >
                  <template #append><StoryRef ids="8.2" /></template>
                </v-textarea>
              </v-card-text>
            </v-card>

            <v-card :elevation="2">
              <v-card-title>Parameters <StoryRef ids="2.2" /></v-card-title>
              <v-card-subtitle class="wrap">
                Declared by the {{ def.name }} extension. Fields marked * are required.
              </v-card-subtitle>
              <v-card-text>
                <ParamField
                  v-for="p in def.params"
                  :key="p.key"
                  v-model="form.values[p.key]"
                  :decl="p"
                  :folders="mock.project?.folders ?? ['/']"
                />
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" md="5" lg="4">
            <v-card :elevation="2" class="mb-4">
              <v-card-title>Address <StoryRef ids="8.1" /></v-card-title>
              <v-card-text>
                <div class="text-break">{{ address }}</div>
                <div class="text-caption text-medium-emphasis mt-1">
                  Each instance gets its own address.
                </div>
              </v-card-text>
            </v-card>
            <v-card :elevation="2">
              <v-card-title>Chart values <StoryRef ids="2.2" /></v-card-title>
              <v-card-subtitle class="wrap">What Kaapana passes to helm.</v-card-subtitle>
              <v-card-text>
                <pre class="values pa-3">{{ chartValues }}</pre>
                <p class="text-caption text-medium-emphasis mt-2 mb-0">
                  Only the parameters on this page change the chart. All other chart values keep the
                  defaults of the
                  {{ def.name }} extension.
                </p>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-alert v-if="invalidFields.length" type="error" variant="tonal" class="mt-4">
          Check {{ invalidFields.length === 1 ? 'this field' : 'these fields' }}:
          {{ invalidFields.join(', ') }}.
        </v-alert>
        <v-alert v-if="dryRun" :type="dryRun.ok ? 'success' : 'error'" variant="tonal" class="mt-4">
          {{ dryRun.message }}
          <StoryRef ids="2.1" />
          <template v-if="!dryRun.ok" #append>
            <v-btn variant="text" size="small" @click="errorOpen = true">Details</v-btn>
          </template>
        </v-alert>

        <div class="d-flex flex-wrap justify-end ga-2 mt-4">
          <v-btn :disabled="busy" to="/catalog">Cancel</v-btn>
          <v-btn :loading="checking" :disabled="busy" @click="check">Check configuration</v-btn>
          <v-btn color="primary" type="submit" :loading="deploying" :disabled="busy">Deploy</v-btn>
        </div>
      </v-form>

      <ConfirmDialog
        v-model="gpuConfirm"
        :title="`Reserve a GPU for “${form.name}”?`"
        text="The GPU stays reserved as long as the application runs, also while nobody works in it. GPUs are shared by all projects."
        confirm-text="Deploy with GPU"
        @confirm="runDeploy"
      />
      <ErrorDetailsDialog
        v-model="errorOpen"
        title="Dry run failed"
        :text="dryRun?.message"
        :error="dryRun?.error ?? null"
      />
    </template>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { notify } from '@kyvg/vue3-notification'
import type { VForm } from 'vuetify/components'
import { ConfirmDialog, ErrorDetailsDialog } from '@kaapana/base-ui'
import ParamField from '@/components/ParamField.vue'
import StoryRef from '@/components/StoryRef.vue'
import UnavailableState from '@/components/UnavailableState.vue'
import type { ParamDecl, ParamValue } from '@/mock/types'
import { roleLabels, useMockStore, type DryRunResult } from '@/stores/mock'

const props = defineProps<{ appId: string }>()
const mock = useMockStore()
const router = useRouter()

// A select cannot show null as a chosen item, so the whole project gets a sentinel.
const WHOLE_PROJECT = '__project__'

const def = computed(() => mock.enabledApps.find((a) => a.id === props.appId))
const blocked = computed(() =>
  def.value && !def.value.multiDeployable
    ? mock.projectApps.find((d) => d.appId === def.value!.id && d.state !== 'UNDEPLOYING')
    : undefined,
)

const form = reactive({
  name: def.value ? mock.suggestName(def.value.id) : '',
  forPerson: WHOLE_PROJECT,
  description: '',
  values: Object.fromEntries((def.value?.params ?? []).map((p) => [p.key, p.default])) as Record<
    string,
    ParamValue
  >,
})

// Dirty means "differs from what the form opened with": a prefilled form that was
// never touched must not block navigation (base-ui guideline "Unsaved changes").
const initial = JSON.stringify(form)
const formRef = ref<InstanceType<typeof VForm> | null>(null)
const checking = ref(false)
const deploying = ref(false)
const busy = computed(() => checking.value || deploying.value)
const dryRun = ref<DryRunResult | null>(null)
const invalidFields = ref<string[]>([])
const gpuConfirm = ref(false)
const errorOpen = ref(false)

watch(
  form,
  () => {
    mock.dirty = JSON.stringify(form) !== initial
    // A result for other values would be misleading.
    dryRun.value = null
  },
  { deep: true },
)
onBeforeUnmount(() => (mock.dirty = false))

const people = computed(() => {
  const members = Object.entries(mock.project?.members ?? {}).map(([id, role]) => ({
    title: mock.personName(id),
    subtitle: roleLabels[role],
    value: id,
  }))
  members.sort((a, b) => a.title.localeCompare(b.title))
  return [
    { title: 'Whole project', subtitle: 'No single scientist', value: WHOLE_PROJECT },
    ...members,
  ]
})

const nameRules = [
  (v: string) => !!v || 'A name is required.',
  (v: string) => !v || (v.length >= 3 && v.length <= 30) || 'Use 3–30 characters.',
  (v: string) =>
    !v ||
    /^[a-z]([a-z0-9-]*[a-z0-9])?$/.test(v) ||
    'Use lowercase letters, digits and hyphens. Start with a letter and do not end with a hyphen.',
  (v: string) =>
    !v ||
    !mock.nameTaken(v) ||
    `${v} is already used in ${mock.project?.name}. Choose another name.`,
]
const descriptionRule = (v: string) => !v || v.length <= 200 || 'Use at most 200 characters.'

const address = computed(() =>
  def.value
    ? mock.instanceUrl({
        projectId: mock.projectId,
        name: form.name || '<name>',
        appId: def.value.id,
      })
    : '',
)

function chartValue(p: ParamDecl): string {
  const v = form.values[p.key]
  if (p.secret) return v ? '<from Kubernetes secret>' : '""'
  if (v === '' || v === null || v === undefined) return '""'
  if (p.type === 'boolean') return v ? 'true' : 'false'
  if (p.type === 'integer') return p.chartSuffix ? `"${v}${p.chartSuffix}"` : String(v)
  return `"${v}"`
}

/** The declared parameters, nested the way helm receives them as values. */
const chartValues = computed(() => {
  type Tree = { [key: string]: Tree | string }
  const tree: Tree = {}
  for (const p of def.value?.params ?? []) {
    const path = p.chartValue.split('.')
    let node = tree
    path.slice(0, -1).forEach((segment) => {
      node[segment] = (node[segment] as Tree) ?? {}
      node = node[segment] as Tree
    })
    node[path[path.length - 1]] = chartValue(p)
  }
  const render = (node: Tree, indent: string): string[] =>
    Object.entries(node).flatMap(([key, value]) =>
      typeof value === 'string'
        ? [`${indent}${key}: ${value}`]
        : [`${indent}${key}:`, ...render(value, indent + '  ')],
    )
  return render(tree, '').join('\n')
})

function fieldLabel(id: string): string {
  if (id === 'field-name') return 'Name'
  if (id === 'field-description') return 'Use case'
  const key = id.replace(/^param-/, '')
  return def.value?.params.find((p) => p.key === key)?.label ?? id
}

async function validate(): Promise<boolean> {
  const result = await formRef.value?.validate()
  invalidFields.value = (result?.errors ?? []).map((e) => fieldLabel(String(e.id)))
  return !!result?.valid
}

async function check() {
  if (!def.value || !(await validate())) return
  checking.value = true
  dryRun.value = await mock.dryRun(def.value.id, form.values)
  checking.value = false
}

async function submit() {
  if (!def.value || !(await validate())) return
  // High-impact: a GPU is a shared, scarce resource that stays reserved.
  if (form.values.gpu === true) gpuConfirm.value = true
  else runDeploy()
}

async function runDeploy() {
  if (!def.value) return
  deploying.value = true
  const result = await mock.dryRun(def.value.id, form.values)
  if (!result.ok) {
    dryRun.value = result
    deploying.value = false
    return
  }
  const app = mock.deploy({
    appId: def.value.id,
    name: form.name,
    description: form.description.trim(),
    forPerson: form.forPerson === WHOLE_PROJECT ? null : form.forPerson,
    values: { ...form.values },
  })
  mock.dirty = false
  notify({
    type: 'success',
    title: 'Deployment started',
    text: `${app.name} is starting in ${mock.project?.name}. Its state changes to Ready when you can open it.`,
  })
  router.push('/applications')
}
</script>

<style scoped>
.values {
  font-family: monospace;
  font-size: 0.8125rem;
  white-space: pre;
  overflow-x: auto;
  background: rgb(var(--v-theme-surface-light));
  border-radius: 8px;
}
.wrap {
  white-space: normal;
}
</style>
