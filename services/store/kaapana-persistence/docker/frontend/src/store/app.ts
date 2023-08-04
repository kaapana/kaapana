// Utilities
import { defineStore } from "pinia";
import axios from "axios";

export const useAppStore = defineStore("app", {
  state: () => ({
    api_base_path: `${location.origin}${import.meta.env.BASE_URL}api`,
    schema_urns: [],
    schemas: new Map(),
  }),
  getters: {
    getSchemaURNs(state) {
      return state.schema_urns;
    },
  },
  actions: {},
});

export enum UploadStatus {
  Started = 1,
  Finished = 2,
  Error = 3,
}

export interface UploadedFileHandle {
  filename: string;
  urn: string | null;
  key: string | null;
  status: UploadStatus;
}

export const useCASStore = defineStore("CAS", {
  state: () => ({
    api_base_path: `${location.origin}${import.meta.env.BASE_URL}api`,
    files: [] as UploadedFileHandle[],
  }),
  getters: {},
  actions: {
    uploadFile(file: File) {
      let formData = new FormData();
      formData.append("file", file);

      var index =
        this.files.push({
          filename: file.name,
          urn: null,
          key: null,
          status: UploadStatus.Started,
        } as UploadedFileHandle) - 1;

      axios
        .post(`${this.api_base_path}/cas/single`, formData)
        .then((response) => {
          this.files[
            index
          ].urn = `urn:kaapana:cas:${response.data.files[0].cas_key}`;
          this.files[index].key = response.data.files[0].cas_key;
          this.files[index].status = UploadStatus.Finished;
        })
        .catch((err) => {
          this.files[index].status = UploadStatus.Error;
        });
    },
    deleteFile(file: UploadedFileHandle) {
      axios
        .delete(`${this.api_base_path}/cas/${file.key}`)
        .then((response) => {
          const index = this.files.findIndex((x) => x.urn === file.urn);
          if (index > -1) {
            this.files.splice(index, 1);
          }
        })
        .catch((err) => {
          // TODO show error message
        });
    },
  },
});

export const useSchemaStore = defineStore("schema", {
  state: () => ({
    api_base_path: `${location.origin}${import.meta.env.BASE_URL}api`,
    // api_base_path: "http://localhost:8000",
    schema_urns: [],
    schemas: new Map(),
    object_urns: [],
  }),
  getters: {
    getSchemaURNs(state) {
      return state.schema_urns;
    },
  },
  actions: {
    fetchSchemaVersion(schema_urn: string) {},
    async fetchSchemaURNs() {
      try {
        const data = await axios.get(`${this.api_base_path}/schema/`);
        this.schema_urns = data.data;
      } catch (error) {
        alert(error);
        console.log(error);
      }
    },
    async fetchObjectURNs(schema_urn: string) {
      try {
        const data = await axios.get(
          `${this.api_base_path}/object/${schema_urn}`
        );
        //this.objects.set("schema_urn", data.data)
        this.object_urns = data.data;
      } catch (error) {
        alert(error);
        console.log(error);
      }
    },
  },
});
