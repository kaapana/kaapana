<template>
    <v-tooltip bottom>
        <template v-slot:activator="{ on }">
            <span v-on="on">
            <v-btn icon v-if="!downloading" :disabled="!canDownload">
                <v-icon
                v-on="on"
                color="primary"
                @click="startDownload"
                >
                mdi-download-circle
                </v-icon>
            </v-btn>
            <v-progress-circular
                :width="3"  
                color="green"                
                indeterminate
                v-if="downloading"
                ></v-progress-circular>
            </span>
        </template>
        <span>{{ status }}</span>
    </v-tooltip>
</template>

<script lang="ts">
import Vue from "vue";
import {
  downloadDatasets
} from "../common/api.service";

export default Vue.extend({
    name: "DownloadDatasetBtn",
    props: {
        selectedSeries: {
            type: Array as () => string[] | null,
            default: []
        }
    },
    data: () => ({
        downloading: false,
        downloadCompleted: false,     
        status: "Download",
        canDownload: true,
    }),
    computed: {
    },
    methods: {
        startDownload(){
            if (this.selectedSeries) {
                const series_joined = this.selectedSeries.join(';');
                this.downloading = true;
                this.canDownload = false;
                this.status = `Downloading ${this.selectedSeries.length} items`;
                downloadDatasets(series_joined).then(() => {
                    this.downloading = false;
                    this.downloadCompleted = true;
                    this.status = 'Ready to Download';
                    this.canDownload = false;
                    setTimeout(this.resetState, 2000);
                }).catch(error => {
                    this.downloading = false;
                    this.status = 'Error on Download';
                    this.canDownload = false;
                    setTimeout(this.resetState, 2000);
                    console.log(error)
                });
            }
        },
        resetState() {
            this.downloading = false;
            this.downloadCompleted = false;
            this.canDownload = true;
            if (this.selectedSeries) {
                this.status = `Download ${this.selectedSeries.length} items`;
            } else {
                this.status = "Download";
            }
        }
    },
    watch: {
        selectedSeries(this: Vue & { status: string; canDownload: boolean }, newval: string[]) {
            if (newval.length > 20) {
                this.status = 'Too many items selected to download. Please use "download-selected-files" to download large amount files';
                this.canDownload = false;
            }else {
                this.status = `Download ${newval.length} items`;
            }
        } 
    },
    mounted() {
        // console.log(this.$store.getters.downloadStarted);
    },
});
</script>

<style scoped></style>