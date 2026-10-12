<template>
  <v-container fluid class="text-left data-upload-view">
    <h1 class="text-h4 mb-4">Data upload</h1>
    <v-alert v-if="projectLoadError" type="error" variant="tonal" class="mb-4">
      {{ projectLoadErrorText }}
      <template #append>
        <v-btn
          variant="text"
          :prepend-icon="kaapanaIcons.refresh"
          :loading="retryingProjectLoad"
          @click="retryProjectLoad"
        >
          Try again
        </v-btn>
        <v-btn variant="text" @click="projectLoadDetails = true">Details</v-btn>
      </template>
    </v-alert>
    <ErrorDetailsDialog
      v-model="projectLoadDetails"
      title="Could not load the project"
      :text="projectLoadErrorText"
      :error="projectLoadError ? apiErrorInfo(projectLoadError) : null"
    />
    <v-alert v-if="isArchived" type="warning" prominent class="mb-4" icon="mdi-archive">
      This project is archived and is read-only. Data upload is disabled. Unarchive the project to
      enable uploads again.
    </v-alert>
    <v-row dense>
      <v-col cols="12">
        <v-card>
          <v-card-title tag="h2" class="text-h5">
            Option 1 (preferred): Using the DICOM receiver port
          </v-card-title>
          <v-card-text>
            <p class="mb-4">
              If you have images locally you can use e.g. DCMTK. However, any tool that sends images
              to a DICOM receiver can be used. Here is an example of sending images with DCMTK:
            </p>
            <code>
              dcmsend -v {{ hostname }} 11112 --scan-directories --aetitle kp-{{
                '<'
              }}dataset-name{{ '>' }} --call kp-{{ projectShortId }} --scan-pattern '*.dcm'
              --recurse {{ '<' }}data-dir-of-DICOM-images{{ '>' }}
            </code>
            <p class="mt-4 mb-2">
              11112 is the default port of the DICOM receiver. Your administrator may have
              configured a different port for this platform.
            </p>
            <p>
              Replace {{ '<' }}dataset-name{{ '>' }} with the dataset that should receive the
              images. DICOM AE titles have at most 16 characters, so the dataset name can have at
              most 13 characters after the kp- prefix.
            </p>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12">
        <v-card :disabled="isArchived">
          <v-card-title tag="h2" class="text-h5">
            Option 2: Upload the data via the browser (experimental)
          </v-card-title>
          <v-card-text>
            <ol class="upload-steps">
              <li class="d-flex align-center ga-3 mb-4">
                <v-icon size="large">mdi-numeric-1-circle</v-icon>
                <div class="d-flex align-center flex-grow-1">
                  Make sure your data is correctly formatted for the upload.
                  <!-- Opening through the activator lets Vuetify return focus to the button. -->
                  <v-dialog v-model="infoDialog" max-width="600">
                    <template #activator="{ props: activatorProps }">
                      <v-btn
                        v-bind="activatorProps"
                        color="primary"
                        icon
                        variant="text"
                        aria-label="How should the uploaded data look?"
                      >
                        <v-icon color="primary">{{ kaapanaIcons.info }}</v-icon>
                      </v-btn>
                    </template>
                    <v-card>
                      <v-card-title tag="h2" class="text-h5">
                        How should the uploaded data look?
                      </v-card-title>
                      <v-card-text>
                        <h3 class="text-h6 mb-2">Upload DICOM data</h3>
                        <p class="mb-4">
                          DICOM data should be uploaded in a single compressed zip file containing
                          folder(s) with DICOM files.
                        </p>
                        <h3 class="text-h6 mb-2">Upload NIfTI data</h3>
                        <p class="mb-2">
                          Since the platform works with the DICOM standard, NIfTI data is converted
                          to DICOM by triggering the workflow
                          <code>import-niftis-from-data-upload</code>. If you have only NIfTI files
                          without segmentations, the files with file endings <code>.nii.gz</code> or
                          <code>.nii</code> can be uploaded in a compressed zip file.
                        </p>
                        <p>
                          For NIfTI data, Kaapana supports multiple ways to specify metadata for
                          volumes and segmentations. Depending on the use case, the data has to be
                          formatted in one of the directory structures described in the
                          <a
                            href="https://kaapana.readthedocs.io/en/stable/user_guide/workflow_management_system/data_upload.html#nifti-data"
                            target="_blank"
                            >Kaapana documentation</a
                          >.
                        </p>
                      </v-card-text>

                      <v-card-actions>
                        <v-spacer></v-spacer>
                        <v-btn color="primary" @click="() => (infoDialog = false)"> Got it! </v-btn>
                      </v-card-actions>
                    </v-card>
                  </v-dialog>
                </div>
              </li>
              <li class="d-flex ga-3 mb-4">
                <v-icon size="large">mdi-numeric-2-circle</v-icon>
                <div class="flex-grow-1">
                  <p class="mb-2">
                    Upload DICOM data, NIfTI data or any other data you want to use in a workflow as
                    a zip file via the drop zone.
                  </p>
                  <Upload
                    label-idle="Drop DICOM, NIfTI or other data here or <span class='filepond--label-action'>browse</span>"
                    :disabled="isArchived"
                    @uploading="postViewDirty"
                  ></Upload>
                </div>
              </li>
              <li class="d-flex align-center ga-3">
                <v-icon size="large">mdi-numeric-3-circle</v-icon>
                <div class="flex-grow-1">
                  <!-- The dialog unmounts its content when it closes, so every opening loads
                       the current list of uploaded files. A forced remount would discard the
                       user's input. -->
                  <v-dialog v-model="workflowDialog" max-width="600">
                    <template #activator="{ props: activatorProps }">
                      <v-btn v-bind="activatorProps" color="primary" :disabled="isArchived">
                        Import the data
                        <v-icon>{{ kaapanaIcons.start }}</v-icon>
                      </v-btn>
                    </template>
                    <WorkflowExecution
                      :onlyLocal="true"
                      kind_of_dags="import"
                      :isDialog="true"
                      @successful="() => (workflowDialog = false)"
                      @cancel="() => (workflowDialog = false)"
                    />
                  </v-dialog>
                </div>
              </li>
            </ol>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import Upload from '@/components/Upload.vue'
import { WorkflowExecution } from '@kaapana/base-ui/workflow-execution'
import '@kaapana/base-ui/workflow-execution.css'
import {
  ErrorDetailsDialog,
  apiErrorInfo,
  apiErrorText,
  kaapanaIcons,
  postViewDirty,
  useProjectStore,
} from '@kaapana/base-ui'
import { settings as defaultSettings } from '@/static/defaultUIConfig'

const projectStore = useProjectStore()
const { selectedProject } = storeToRefs(projectStore)
// A disabled card only blocks the pointer, so each control is disabled too.
// Otherwise the keyboard still reaches them.
const isArchived = computed(() => selectedProject.value.is_archived === true)
// Until the project is known, the example uses the placeholder of the user guide.
const projectShortId = computed(() => selectedProject.value.short_id ?? '<project-short-id>')

const workflowDialog = ref(false)
const infoDialog = ref(false)
const hostname = window.location.hostname

// selectedProject drives the archived guard and the dcmsend example, so a failed
// lookup stays visible on the page instead of in a notification that disappears.
const projectLoadError = ref<unknown>(null)
const projectLoadDetails = ref(false)
const retryingProjectLoad = ref(false)
const projectLoadErrorText = computed(() =>
  projectLoadError.value ? apiErrorText(projectLoadError.value, 'Could not load the project.') : '',
)

function loadProject() {
  return projectStore
    .getSelectedProject()
    .then(() => {
      projectLoadError.value = null
    })
    .catch((error: unknown) => {
      projectLoadError.value = error
    })
}

function retryProjectLoad() {
  retryingProjectLoad.value = true
  loadProject().finally(() => {
    retryingProjectLoad.value = false
  })
}

loadProject()
// WorkflowExecution reads localStorage["settings"] directly; seed it for
// standalone boots the shell never touched.
if (!localStorage['settings']) {
  localStorage['settings'] = JSON.stringify(defaultSettings)
}
</script>

<style scoped>
/* The page is mostly text and one form, so it does not need the full width
   of a wide display. The container centres itself in the space beyond. */
.data-upload-view {
  max-width: 1200px;
}

/* The numbered icons mark the steps, so the list needs no markers of its own. */
.upload-steps {
  list-style: none;
  padding-left: 0;
}
</style>
