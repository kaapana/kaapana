<template>
  <v-dialog v-model="remoteDialog" max-width="600px">
    <template v-slot:activator="{ props }">
      <v-btn v-bind="props" color="primary" size="small" rounded variant="outlined">
        add remote
      </v-btn>
    </template>
    <v-card>
      <v-form ref="remoteFormRef" v-model="remoteValid">
        <v-card-title><span class="text-h5">Remote Instance</span></v-card-title>
        <v-card-text>
          <v-tabs v-model="tab">
            <v-tab value="manual">Manual</v-tab>
            <v-tab value="paste">Paste Config</v-tab>
          </v-tabs>
          <!-- `eager` keeps both panes mounted so the manual fields stay
               registered with the form: submitting from the Paste tab must
               still trigger the required-field validation below. -->
          <v-tabs-window v-model="tab">
            <v-tabs-window-item value="manual" eager>
              <v-container>
                <v-row>
                  <v-col cols="12">
                    <v-text-field v-model="remotePost.instance_name" label="Instance name" :rules="requiredRule" :disabled="remoteUpdate"></v-text-field>
                  </v-col>
                </v-row>
                <v-row>
                  <v-col cols="12">
                    <v-text-field v-model="remotePost.host" label="Host" :rules="requiredRule" :disabled="remoteUpdate"></v-text-field>
                  </v-col>
                </v-row>
                <v-row>
                  <v-col cols="8">
                    <v-text-field v-model="remotePost.port" label="Port" type="number"></v-text-field>
                  </v-col>
                  <v-col cols="4">
                    <v-checkbox v-model="remotePost.ssl_check" label="Verify SSL"></v-checkbox>
                  </v-col>
                </v-row>
                <v-row>
                  <v-col cols="12">
                    <v-text-field v-model="remotePost.token" label="Token" :rules="requiredRule"></v-text-field>
                  </v-col>
                </v-row>
                <v-row>
                  <v-col cols="12">
                    <v-text-field v-model="remotePost.fernet_key" label="Fernet Key"></v-text-field>
                  </v-col>
                </v-row>
              </v-container>
            </v-tabs-window-item>
            <v-tabs-window-item value="paste" eager>
              <v-container>
                <v-row>
                  <v-col cols="12">
                    <v-textarea
                      v-model="pasteRemote"
                      label="Paste remote instance definition as json string"
                      placeholder="{
                        'instance_name': '<instance_name>',
                        'host': '<host>',
                        'port': '<port>',
                        'token': '<token>',
                        'fernet_key': '<fernet_key>',
                        'ssl_check': '<true/false>'
                      }"
                      rows="8"
                      variant="outlined"
                    ></v-textarea>
                  </v-col>
                </v-row>
              </v-container>
            </v-tabs-window-item>
          </v-tabs-window>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn class="mr-4" @click="submitRemoteForm">submit</v-btn>
          <v-btn @click="resetForm">clear</v-btn>
        </v-card-actions>
      </v-form>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { notify } from '@kyvg/vue3-notification'
import { kaapanaApiService } from '@kaapana/base-ui'

interface RemotePost {
  ssl_check: boolean
  token: string
  host: string
  instance_name: string
  port: number | string
  fernet_key: string
}

const emit = defineEmits<{ refreshRemoteFromAdding: [] }>()

function initialRemotePost(): RemotePost {
  return {
    ssl_check: false,
    token: '',
    host: '',
    instance_name: '',
    port: 443,
    fernet_key: 'deactivated',
  }
}

const remoteValid = ref(false)
const remoteUpdate = ref(false)
const remoteDialog = ref(false)
const tab = ref('manual')
const pasteRemote = ref('')
const remotePost = reactive<RemotePost>(initialRemotePost())
const remoteFormRef = ref<any>(null)

const requiredRule = computed(() => [(v: any) => !!v || 'This field is required'])

watch(pasteRemote, () => {
  try {
    const jsonData = JSON.parse(pasteRemote.value)
    remotePost.instance_name = jsonData.hasOwnProperty('instance_name')
      ? jsonData['instance_name']
      : remotePost.instance_name
    remotePost.host = jsonData.hasOwnProperty('host') ? jsonData['host'] : remotePost.host
    remotePost.port = jsonData.hasOwnProperty('port') ? jsonData['port'] : remotePost.port
    remotePost.token = jsonData.hasOwnProperty('token') ? jsonData['token'] : remotePost.token
    remotePost.fernet_key = jsonData.hasOwnProperty('fernet_key')
      ? jsonData['fernet_key']
      : remotePost.fernet_key
    remotePost.ssl_check = jsonData.hasOwnProperty('ssl_check')
      ? jsonData['ssl_check']
      : remotePost.ssl_check
  } catch {
    notify({
      type: 'error',
      title: 'Please enter the instance definition in the correct json format with all fields defined!',
    })
  }
})

function resetForm() {
  remoteValid.value = false
  remoteUpdate.value = false
  remoteDialog.value = false
  tab.value = 'manual'
  pasteRemote.value = ''
  Object.assign(remotePost, initialRemotePost())
}

async function submitRemoteForm() {
  const { valid } = await remoteFormRef.value.validate()
  if (!valid) {
    return
  }
  kaapanaApiService
    .federatedClientApiPost('/remote-kaapana-instance', remotePost)
    .then(() => {
      remoteDialog.value = false
      emit('refreshRemoteFromAdding')
      resetForm()
    })
    .catch((err: any) => {
      console.log(err)
      notify({
        type: 'error',
        title: 'Failed to add remote instance',
        text: err?.response?.data?.detail ?? err.message,
      })
    })
}
</script>
