<template>
  <div class="dropzone">
    <v-container fluid class="text-left">
      <h1>Data upload</h1>
      <v-alert v-if="selectedProject && selectedProject.is_archived" type="warning" prominent class="mb-4" icon="mdi-archive">
        This project is archived and is read-only. Data upload is disabled.
        Unarchive the project to enable uploads again.
      </v-alert>
      <v-row dense>
        <v-col cols="12">
          <v-card>
            <v-card-title class="text-h5">
              Option 1 (preferred): Using the DICOM receiver port.
            </v-card-title>
            <v-card-text>
              If you have images locally you can use e.g. DCMTK. However, any tool that
              sends images to a DICOM receiver can be used. Here is an example of sending
              images with DCMTK:
              <br />
              <br />
              <code>
                dcmsend -v {{ hostname }} 11112 --scan-directories --aetitle
                kp-{{ "<" }}dataset-name{{ ">" }} --call
                kp-{{ selectedProject.short_id }} --scan-pattern '*.dcm' --recurse
                {{ "<" }}data-dir-of-DICOM-images{{ ">" }}
              </code>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12">
          <v-card :disabled="selectedProject && selectedProject.is_archived">
            <v-card-title class="text-h5">
              Option 2: Upload the data via the browser(experimental).
            </v-card-title>
            <v-card-text>
              <v-icon class="my-2" size="large">mdi-numeric-1-circle</v-icon>&nbsp; Make sure
              your data is correctly formatted for the upload.
              <v-btn color="primary" icon variant="text" @click.stop="infoDialog = true">
                <v-icon color="primary"> mdi-information </v-icon>
              </v-btn>
              <br />

              <v-dialog v-model="infoDialog" width="60vw">
                <v-card>
                  <v-card-title class="text-h5">
                    How should the uploaded data look like?
                  </v-card-title>
                  <v-card-text>
                    <h3>Upload of DICOM data</h3>
                    <p>
                      DICOM data should be uploaded in a single compressed zip-file
                      containing folder(s) with DICOM files.
                    </p>
                    <h3>Upload NIfTI data</h3>
                    <p>
                      Since the platform works with the DICOM standard, NIfTI data is
                      converted to DICOMs by triggering the workflow
                      `convert-nifitis-to-dicoms-and-import-to-pacs`. If you have only
                      NIfTI files without segmentations, the files with file endings
                      `.nii.gz` or `.nii` can be uploaded in a compressed zip-file.
                    </p>
                    <p>
                      For NIfTI data kaapana supports multiple ways to specify metadata
                      for volumes and segmentations. Depending on the use case the data
                      has to be formated in one of the directory structures described in
                      the
                      <a href="https://kaapana.readthedocs.io/en/stable/user_guide/workflows.html#import-uploaded-nifti-files"
                        target="_blank">Kaapana documentation</a>.
                    </p>
                  </v-card-text>

                  <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn color="primary" @click="() => (infoDialog = false)">
                      Got it!
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-dialog>

              <v-icon class="my-2" size="large">mdi-numeric-2-circle</v-icon>&nbsp; Upload
              DICOMS, NIfTIs or any data you want to use in a workflow as a zip file via
              the dropzone.
              <Upload label-idle="Dicoms, ITK images or any other data" :on-process-file="fileComplete"></Upload>
              <br />
              <v-icon size="large">mdi-numeric-3-circle</v-icon>&nbsp;
              <v-btn color="primary" @click="() => (workflowDialog = true)">
                Import the data
                <v-icon>mdi-play-outline</v-icon>
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>

        <v-dialog v-model="workflowDialog" width="500">
          <v-defaults-provider :defaults="underlinedFieldDefaults">
            <WorkflowExecution :key="componentKey" :onlyLocal="true" kind_of_dags="import" :isDialog="true"
              @successful="() => (workflowDialog = false)" @cancel="() => (workflowDialog = false)" />
          </v-defaults-provider>
        </v-dialog>
      </v-row>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { notify } from '@kyvg/vue3-notification'
import Upload from '@/components/Upload.vue'
import { WorkflowExecution } from '@kaapana/base-ui/workflow-execution'
import '@kaapana/base-ui/workflow-execution.css'
import { useProjectStore } from '@kaapana/base-ui'
import { settings as defaultSettings } from '@/static/defaultUIConfig'

const projectStore = useProjectStore()
const { selectedProject } = storeToRefs(projectStore)

// This view standardizes the workflow form on underlined fields; supplied via a
// defaults-provider around the shared WorkflowExecution (which carries no inline
// variants). Covers both the native template fields and the vjsf-rendered ones.
const underlinedFieldDefaults = {
  VTextField: { variant: 'underlined' },
  VSelect: { variant: 'underlined' },
  VAutocomplete: { variant: 'underlined' },
  VCombobox: { variant: 'underlined' },
  VTextarea: { variant: 'underlined' },
  VNumberInput: { variant: 'underlined' },
}

const workflowDialog = ref(false)
const infoDialog = ref(false)
const supported = ref(true)
const componentKey = ref(0)
const hostname = ref('')

// selectedProject drives the archived guard and the dcmsend example.
projectStore.getSelectedProject().catch((error: any) => {
  notify({
    title: 'Error',
    text: error.response?.data?.detail ?? error.message,
    type: 'error',
  })
})
// WorkflowExecution reads localStorage["settings"] directly; seed it for
// standalone boots the shell never touched.
if (!localStorage['settings']) {
  localStorage['settings'] = JSON.stringify(defaultSettings)
}

onMounted(() => {
  const { userAgent } = navigator
  if (userAgent.includes('Firefox/')) {
    supported.value = false
  } else {
    supported.value = true
  }
  hostname.value = window.location.hostname
})

function fileComplete(_error: any, _file: any) {
  // Remount WorkflowExecution (:key) so the import form reflects the new upload.
  componentKey.value += 1
}
</script>

<style lang="scss">
.upload {
  margin-top: 10px;
  padding-top: 100px;
  padding-bottom: 10px;
}
</style>
