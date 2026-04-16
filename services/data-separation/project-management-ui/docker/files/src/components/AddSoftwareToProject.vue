<template>
  <v-card prepend-icon="mdi-workflow" title="Add Workflow to Project">
    <v-overlay v-model="fetching" class="align-center justify-center" contained>
      <v-progress-circular color="primary" indeterminate></v-progress-circular>
    </v-overlay>

    <v-card-text>
      <v-container>
        <v-row
          ><v-text-field
            v-model="projectNameVal"
            label="Project Name"
            disabled
            required
          ></v-text-field
        ></v-row>
        <v-row>
          <v-autocomplete
            v-model="softwareUuid"
            label="Workflow / DAG"
            :disabled="actionType == 'update'"
            :items="software"
            item-title="software_uuid"
            item-value="software_uuid"
            :loading="fetching"
            clearable
            chips
            small-chips
            multiple
          >
            <template #chip="{ props, item }">
              <v-chip v-bind="props">
                <v-chip-text>{{ item.raw.software_uuid }}</v-chip-text>
              </v-chip>
            </template>
          </v-autocomplete>
        </v-row>
        <v-row v-if="software.length > 0" class="mt-2">
          <v-col>
            <v-alert type="info" variant="tonal" icon="mdi-information">
              <div class="text-body-2">
                <strong>Tip:</strong> Select workflows that this project is allowed to execute.
                <br>
                <span class="text-caption">Available workflows: {{ software.length }}</span>
              </div>
            </v-alert>
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
    <v-card-actions>
      <v-container>
        <v-row>
          <v-col cols="6">
            <v-btn
              color="surface-variant"
              size="large"
              variant="elevated"
              block
              @click="cancel"
              >Cancel</v-btn
            >
          </v-col>
          <v-col cols="6">
            <v-btn
              :disabled="!valid || !softwareUuid || softwareUuid.length === 0"
              color="success"
              size="large"
              variant="elevated"
              block
              @click="submit"
              >Add</v-btn
            >
          </v-col>
        </v-row>
      </v-container>
    </v-card-actions>
  </v-card>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from "vue";
import { aiiApiPost, kaapanaPluginGet } from "@/common/services";
import { Software } from "@/common/types";

const props = defineProps({
  projectName: {
    type: String,
    required: true,
  },
  projectId: {
    type: String,
    required: true,
  },
  currentSoftware: {
    type: Array<Software>,
  },
  oncancel: {
    type: Function,
  },
  onsuccess: {
    type: Function,
  },
});

const projectNameVal = ref(props.projectName);
const fetching = ref(false);
const software = ref<Software[]>([]);
const softwareUuid = ref("");

const valid = computed(() => {
  return props.projectId.trim() !== "" && props.projectName.trim() !== "" && softwareUuid.value.trim() !== "";
});

onMounted(async () => {
  fetchAvailableSoftware();
});

const fetchAvailableSoftware = async () => {
  let currentSoftwareUuids: string[] = [];
  if (props.currentSoftware) {
    currentSoftwareUuids = props.currentSoftware.map((software: Software) => software.software_uuid);
  }
  try {
    const fetchedSoftware = await kaapanaPluginGet(`getdags`);
    fetching.value = false;
    let fetchedSoftwareUids = Object.keys(fetchedSoftware)
    let filteredSoftwareUuids = fetchedSoftwareUids.filter(
      (uuid: string) => !currentSoftwareUuids.includes(uuid)
    );
    let sortedSoftwareUuids = filteredSoftwareUuids.sort((a, b) => {
      return a.localeCompare(b);
    });

    software.value = sortedSoftwareUuids.map((uuid: any) => {
      return {
        software_uuid: uuid,
      };
    });
  } catch (error: unknown) {
    fetching.value = false;
  }
};

const submit = async () => {
  // console.log(props.projectName, roleName.value, userId.value);
  const data = {
    project_id: props.projectId.trim(),
    software_uuid: softwareUuid.value.trim(),
  };
  fetching.value = true;
  addNewSoftwareMapping(data);
};

const cancel = () => {
  props.oncancel?.();
};

const addNewSoftwareMapping = async (data: any) => {
  const params = [
    {
      software_uuid: data["software_uuid"],
    },
  ];
  try {
    await aiiApiPost(`projects/${data["project_id"]}/software-mappings`, params);
    fetching.value = false;
    props.onsuccess?.();
  } catch (error: unknown) {
    fetching.value = false;
    props.onsuccess?.(false);
  }
};
</script>
