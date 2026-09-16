<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import { kaapanaIcons } from '@kaapana/base-ui'
import { fetchResultsTree, type ResultsTreeNode } from '@/api/results'
import IFrameWindow from '@/components/IFrameWindow.vue'

// The backend node plus the paging and loading state the tree keeps per folder.
interface TreeNode extends ResultsTreeNode {
  children?: TreeNode[]
  nextContinuationToken?: string | null
  loadingMore?: boolean
  childrenLoaded?: boolean
}

// Small page size keeps a single "Load more" burst renderable: VTreeview has no
// virtualization, so a full 500-node page freezes the tab on render.
const PAGE_SIZE = 100
// Opening a whole folder's subtree past this many results asks first.
const OPEN_CONFIRM_THRESHOLD = 10
const MAX_CASCADE_FILES = 300
// The file cap alone does not bound the work: only .html objects become files, so
// result-less folders and empty continuation pages spend requests without ever
// reaching it.
const MAX_CASCADE_REQUESTS = 300

// The open preview panel, keyed by result path rather than by position, so
// that removing a result cannot point it at a different one.
const panel = ref<string | null>(null)
const staticUrls = ref<TreeNode[]>([])
const rootNextContinuationToken = ref<string | null>(null)
const rootLoadingMore = ref(false)
const rootLoading = ref(false)
// A folder cascade fetches unloaded descendants directly (bypassing VTreeview's
// per-node spinner), so surface its own progress or a deep check feels frozen.
const cascadeLoading = ref(false)
const search = ref<string | null>(null)
const tree = ref<TreeNode[]>([])

const confirmDialog = ref(false)
const confirmCount = ref(0)
const cancelButton = ref<ComponentPublicInstance | null>(null)
let pendingCascade: { folder: TreeNode; files: TreeNode[]; truncated: boolean } | null = null
// Incremented synchronously around our own writes to `tree` so the selection
// watcher ignores them and only reacts to user checkbox changes. A counter (not
// a boolean) survives two guarded writes overlapping across a nextTick.
let suppressSelectionWatch = 0

const isFolder = (node: TreeNode) => !node.file

// The backend emits `children: []` + hasChildren on every node; Vuetify treats
// any defined `children` as an expandable group, so a file with `children: []`
// gets a bogus expand toggle. Strip the key from leaves, keep it on folders.
function normalizeNodes(items: ResultsTreeNode[]): TreeNode[] {
  return items.map((item: TreeNode) => {
    if (item.hasChildren === false) {
      const { children: _dropped, ...leaf } = item
      return leaf
    }
    return item
  })
}

const FILE_ICONS: Record<string, string> = {
  html: 'mdi-language-html5',
  js: 'mdi-nodejs',
  json: 'mdi-code-json',
  md: 'mdi-language-markdown',
  pdf: 'mdi-file-pdf',
  png: 'mdi-file-image',
  txt: 'mdi-file-document-outline',
  xls: 'mdi-file-excel',
}
const FALLBACK_FILE_ICON = 'mdi-file-outline'

// Only .html objects reach the tree today, so an unlisted extension would
// otherwise render an empty icon slot rather than nothing at all.
const fileIcon = (node: TreeNode) => FILE_ICONS[node.file as string] ?? FALLBACK_FILE_ICON

// VTreeview types its slot payload as unknown; every slot here is a result node.
const asNode = (item: unknown): TreeNode => item as TreeNode

const selectedFiles = computed(() => tree.value.filter((item) => item.file && item.url))

// Expand the result that was just added. Reacting to removals as well would
// collapse whatever the user is reading whenever another result is unchecked.
watch(selectedFiles, (newValue, oldValue) => {
  const previous = new Set(oldValue.map((node) => node.path))
  const added = newValue.filter((node) => !previous.has(node.path))
  if (added.length) {
    panel.value = added[added.length - 1].path
  }
})

function notifyLoadFailed(text: string) {
  notify({ type: 'error', title: 'Could not load results', text })
}

function getStaticWebsiteResults() {
  rootLoading.value = true
  fetchResultsTree({ limit: PAGE_SIZE })
    .then((page) => {
      staticUrls.value = normalizeNodes(page.items)
      rootNextContinuationToken.value = page.nextContinuationToken
    })
    .catch((error) => {
      console.error('Failed to load workflow results:', error)
      notifyLoadFailed('The workflow results could not be loaded. Please try again.')
    })
    .finally(() => {
      rootLoading.value = false
    })
}

// Returns false on fetch failure so both callers can act on it: the cascade
// treats it as terminal, the interactive expand path reports it.
async function fetchChildren(rawItem: unknown): Promise<boolean> {
  const item = asNode(rawItem)
  if (item.file || item.childrenLoaded) {
    return true
  }

  try {
    const page = await fetchResultsTree({ prefix: item.path, limit: PAGE_SIZE })
    item.children = normalizeNodes(page.items)
    item.nextContinuationToken = page.nextContinuationToken
    item.childrenLoaded = true
    return true
  } catch (error) {
    item.children = []
    item.nextContinuationToken = null
    item.childrenLoaded = true
    return false
  }
}

// VTreeview's :load-children expects a void promise; keep awaiting so its
// per-node spinner still shows. Reporting here rather than in fetchChildren keeps
// the cascade's own failure toast from doubling up.
const loadChildren = (rawItem: unknown): Promise<void> =>
  fetchChildren(rawItem).then((loaded) => {
    if (!loaded) {
      notifyLoadFailed('The folder contents could not be loaded. Please try again.')
    }
  })

// Returns false on failure. The token is deliberately LEFT set on error so the
// interactive "Load more" button stays retryable -- the cascade must not spin on
// that (it inspects the return value instead of the surviving token).
async function loadMoreForNode(item: TreeNode): Promise<boolean> {
  if (!item.nextContinuationToken) {
    return true
  }

  item.loadingMore = true
  try {
    const page = await fetchResultsTree({
      prefix: item.path,
      continuationToken: item.nextContinuationToken,
      limit: PAGE_SIZE,
    })
    item.children = (item.children || []).concat(normalizeNodes(page.items))
    item.nextContinuationToken = page.nextContinuationToken
    return true
  } catch (error) {
    console.error('Failed to load more workflow result children:', error)
    return false
  } finally {
    item.loadingMore = false
  }
}

// The template's per-folder "Load more" drops loadMoreForNode's boolean; the
// cascade inspects it itself, so only the interactive path reports here.
async function loadMoreChildren(item: TreeNode) {
  if (!(await loadMoreForNode(item))) {
    notifyLoadFailed('The next page of folder results could not be loaded. Please try again.')
  }
}

async function loadMoreRootResults() {
  if (!rootNextContinuationToken.value) {
    return
  }

  rootLoadingMore.value = true
  try {
    const page = await fetchResultsTree({
      continuationToken: rootNextContinuationToken.value,
      limit: PAGE_SIZE,
    })
    staticUrls.value = staticUrls.value.concat(normalizeNodes(page.items))
    rootNextContinuationToken.value = page.nextContinuationToken
  } catch (error) {
    console.error('Failed to load more root workflow results:', error)
    notifyLoadFailed('The next page of results could not be loaded. Please try again.')
  } finally {
    rootLoadingMore.value = false
  }
}

// Folder paths arrive with or without a trailing slash depending on the backend
// call; normalize so descendant prefix-matching is unambiguous.
const withTrailingSlash = (path: string) => (path.endsWith('/') ? path : `${path}/`)

// Every write to the selection model we make ourselves (cascade add, revert,
// descendant prune) goes through here so the watcher below skips our own churn.
async function setSelection(nodes: TreeNode[]) {
  suppressSelectionWatch += 1
  tree.value = nodes
  await nextTick()
  suppressSelectionWatch -= 1
}

const isStillSelected = (folder: TreeNode) =>
  tree.value.some((node) => node.path === folder.path)

function unselectFolder(folder: TreeNode) {
  return setSelection(tree.value.filter((node) => node.path !== folder.path))
}

function notifyTruncated() {
  notify({
    type: 'warn',
    title: 'Too many results',
    text: 'This folder is too large to open at once. Open the remaining folders individually.',
  })
}

// Load one folder within the request budget. A fetch failure throws so the cascade
// stops instead of retrying the token forever; an exhausted budget keeps the token
// so the interactive "Load more" still works and reports `incomplete`.
async function loadWholeFolder(
  folder: TreeNode,
  budget: { left: number },
): Promise<{ children: TreeNode[]; incomplete: boolean }> {
  if (!folder.childrenLoaded && budget.left > 0) {
    budget.left -= 1
    if (!(await fetchChildren(folder))) {
      throw new Error('cascade: failed to load folder children')
    }
  }
  while (folder.nextContinuationToken && budget.left > 0) {
    budget.left -= 1
    if (!(await loadMoreForNode(folder))) {
      throw new Error('cascade: failed to load a continuation page')
    }
  }
  return {
    children: folder.children || [],
    incomplete: !folder.childrenLoaded || !!folder.nextContinuationToken,
  }
}

// Capped at MAX_CASCADE_FILES results and MAX_CASCADE_REQUESTS fetches so a huge
// run can't hang the browser; either ceiling reports back as `truncated`.
async function collectSubtreeFiles(
  folder: TreeNode,
): Promise<{ files: TreeNode[]; truncated: boolean }> {
  const files: TreeNode[] = []
  const folders: TreeNode[] = [folder]
  const budget = { left: MAX_CASCADE_REQUESTS }
  let truncated = false

  while (folders.length && !truncated) {
    const { children, incomplete } = await loadWholeFolder(folders.shift()!, budget)
    if (incomplete) {
      truncated = true
    }
    for (const child of children) {
      if (child.file && child.url) {
        files.push(child)
        if (files.length >= MAX_CASCADE_FILES) {
          truncated = true
          break
        }
      } else if (isFolder(child)) {
        folders.push(child)
      }
    }
  }
  return { files, truncated }
}

async function addFilesToSelection(files: TreeNode[]) {
  const present = new Set(tree.value.map((node) => node.path))
  const additions = files.filter((file) => !present.has(file.path))
  if (additions.length) {
    await setSelection([...tree.value, ...additions])
  }
}

async function cascadeSelectFolder(folder: TreeNode) {
  cascadeLoading.value = true
  let files: TreeNode[]
  let truncated: boolean
  try {
    ;({ files, truncated } = await collectSubtreeFiles(folder))
  } catch (error) {
    console.error('Failed to open folder results:', error)
    notify({
      type: 'error',
      title: 'Could not open folder',
      text: 'Some results failed to load, so the folder was not opened. Please try again.',
    })
    await unselectFolder(folder)
    return
  } finally {
    cascadeLoading.value = false
  }

  // The user may have unchecked the folder while we were fetching.
  if (!isStillSelected(folder)) {
    return
  }
  if (!files.length) {
    if (truncated) {
      notifyTruncated()
    }
    return
  }
  if (files.length > OPEN_CONFIRM_THRESHOLD) {
    // Only one confirm at a time: don't clobber a pending prompt.
    if (confirmDialog.value) {
      notify({
        type: 'warn',
        title: 'One folder at a time',
        text: 'Answer the open prompt before opening another large folder.',
      })
      await unselectFolder(folder)
      return
    }
    pendingCascade = { folder, files, truncated }
    confirmCount.value = files.length
    confirmDialog.value = true
    return
  }
  await addFilesToSelection(files)
  if (truncated) {
    notifyTruncated()
  }
}

async function confirmCascade() {
  confirmDialog.value = false
  if (!pendingCascade) {
    return
  }
  const { folder, files, truncated } = pendingCascade
  pendingCascade = null
  if (!isStillSelected(folder)) {
    return
  }
  await addFilesToSelection(files)
  if (truncated) {
    notifyTruncated()
  }
}

// Dismissing the dialog any way at all -- Cancel, Escape, a click outside --
// has to leave the folder unchecked, or it would stay ticked without its
// results ever opening.
async function cancelPendingCascade() {
  if (pendingCascade) {
    const { folder } = pendingCascade
    pendingCascade = null
    await unselectFolder(folder)
  }
}

function cancelCascade() {
  confirmDialog.value = false
}

// Focus the safe action, so confirming a large open takes a deliberate move.
// The dialog otherwise focuses its own content element once it has opened.
function focusCancelButton() {
  const button = cancelButton.value?.$el as HTMLElement | undefined
  button?.focus()
}

// Unchecking a folder drops its already-selected descendants from the selection
// (independent strategy does not cascade, so we do it by path prefix).
async function removeSubtreeFromSelection(folders: TreeNode[]) {
  const prefixes = folders.map((folder) => withTrailingSlash(folder.path))
  const kept = tree.value.filter((node) => !prefixes.some((prefix) => node.path.startsWith(prefix)))
  if (kept.length !== tree.value.length) {
    await setSelection(kept)
  }
}

// The independent select strategy adds files as-is but leaves folder handling to
// us: react to folder check/uncheck here and cascade over the subtree.
watch(tree, async (newSelection, oldSelection) => {
  if (suppressSelectionWatch > 0) {
    return
  }
  const oldPaths = new Set(oldSelection.map((node) => node.path))
  const newPaths = new Set(newSelection.map((node) => node.path))
  const addedFolders = newSelection.filter((node) => isFolder(node) && !oldPaths.has(node.path))
  const removedFolders = oldSelection.filter((node) => isFolder(node) && !newPaths.has(node.path))

  if (removedFolders.length) {
    await removeSubtreeFromSelection(removedFolders)
  }
  for (const folder of addedFolders) {
    await cascadeSelectFolder(folder)
  }
})

function openExternalPage(url: string) {
  window.open(url, '_blank')
}

onMounted(() => {
  getStaticWebsiteResults()
})
</script>

<template>
  <v-container class="text-left" fluid>
    <v-row>
      <v-col cols="3">
        <v-card>
          <v-text-field
            v-model="search"
            label="Search loaded results"
            hint="Search only filters folders and files that have already been loaded."
            persistent-hint
            hide-details="auto"
            variant="outlined"
            density="compact"
            prepend-inner-icon="mdi-magnify"
            clearable
            clear-icon="mdi-close-circle-outline"
          />
          <v-progress-linear v-if="rootLoading || cascadeLoading" indeterminate color="primary" />
          <v-treeview
            v-model:selected="tree"
            :items="staticUrls"
            :search="search || undefined"
            item-value="path"
            item-title="name"
            selectable
            select-strategy="independent"
            return-object
            activatable
            open-on-click
            :load-children="loadChildren"
          >
            <template #prepend="{ item, isOpen }">
              <v-icon v-if="!asNode(item).file">
                {{ isOpen ? 'mdi-folder-open' : 'mdi-folder' }}
              </v-icon>
              <v-icon v-else>
                {{ fileIcon(asNode(item)) }}
              </v-icon>
            </template>
            <template #title="{ item }">
              <span class="text-wrap">{{ asNode(item).name }}</span>
            </template>
            <template #append="{ item }">
              <v-btn
                v-if="!asNode(item).file && asNode(item).nextContinuationToken"
                size="x-small"
                variant="text"
                color="primary"
                :loading="asNode(item).loadingMore"
                @click.stop="loadMoreChildren(asNode(item))"
              >
                Load more
              </v-btn>
            </template>
          </v-treeview>
          <v-card-actions v-if="rootNextContinuationToken">
            <v-btn
              variant="text"
              color="primary"
              :loading="rootLoadingMore"
              @click="loadMoreRootResults"
            >
              Load more root results
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <v-col cols="9">
        <div v-if="selectedFiles.length == 0">
          <h1>Workflow results</h1>
          <p>Results from the workflows will be shown here!</p>
          <v-icon class="results-icon">mdi-chart-bar-stacked</v-icon>
        </div>
        <v-expansion-panels v-model="panel" variant="accordion">
          <v-expansion-panel v-for="node in selectedFiles" :key="node.path" :value="node.path">
            <v-expansion-panel-title>
              <span class="d-flex align-center ga-2">
                <span class="text-truncate">{{ node.name }}</span>
                <v-btn
                  icon
                  :aria-label="`Open ${node.name} in a new tab`"
                  color="primary"
                  variant="text"
                  density="comfortable"
                  size="small"
                  @click.stop="openExternalPage(node.url!)"
                >
                  <v-icon>{{ kaapanaIcons.externalLink }}</v-icon>
                  <v-tooltip activator="parent" location="bottom">{{ node.url }}</v-tooltip>
                </v-btn>
              </span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <IFrameWindow :iFrameUrl="node.url!" width="100%" height="100%" />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-col>
    </v-row>

    <v-dialog
      v-model="confirmDialog"
      max-width="400"
      @after-enter="focusCancelButton"
      @after-leave="cancelPendingCascade"
    >
      <v-card>
        <v-card-title>Open {{ confirmCount }} results?</v-card-title>
        <v-card-text>
          This folder contains {{ confirmCount }} results. Opening them all at once may take a
          moment.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn ref="cancelButton" variant="text" @click="cancelCascade">Cancel</v-btn>
          <v-btn color="primary" variant="text" @click="confirmCascade">Open all</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<style lang="scss">
.results-icon {
  font-size: 425px !important;
  text-align: center;
  width: 100%;
}
</style>
