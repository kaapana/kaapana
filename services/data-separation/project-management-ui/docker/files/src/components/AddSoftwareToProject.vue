<template>
  <v-card prepend-icon="mdi-gamepad-variant" title="Add software to Project">
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
        <!-- <v-row><v-text-field v-model="userId" label="User ID"></v-text-field></v-row> -->
        <v-row>
          <v-select
            v-model="softwareUuid"
            label="Software"
            :items="software"
            item-title="software_uuid"
            item-value="software_uuid"
          />
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
              :disabled="!valid"
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
import { aiiApiPost, kaapanaPluginGet } from "@/common/aiiApi.service";
import { Software } from "@/common/types";

const props = defineProps({
  projectName: {
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
  return props.projectName.trim() !== "" && softwareUuid.value.trim() !== "";
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
    software.value = filteredSoftwareUuids.map((uuid: any) => {
      return {
        software_uuid: uuid,
      };
    });
    console.log(software.value);
  } catch (error: unknown) {
    fetching.value = false;
  }
};

const submit = async () => {
  // console.log(props.projectName, roleName.value, userId.value);
  const data = {
    project_name: props.projectName.trim(),
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
    await aiiApiPost(`projects/${data["project_name"]}/software-mappings`, params);
    fetching.value = false;
    props.onsuccess?.();
  } catch (error: unknown) {
    fetching.value = false;
    props.onsuccess?.(false);
  }
};
</script>
