<template>
    <v-menu offset-y bottom left>
        <template v-slot:activator="{ on: menu, attrs }">
            <v-tooltip bottom>
                <template v-slot:activator="{ on: tooltip }">
                    <v-btn icon v-bind="attrs" v-on="{ ...tooltip, ...menu }">
                        <v-icon color="primary">
                            mdi-download-circle
                        </v-icon>
                    </v-btn>
                </template>
                <span>Download</span>
            </v-tooltip>
        </template>
        <v-list>
            <v-list-item>
                <v-list-item-title>Download List</v-list-item-title>
            </v-list-item>
            <v-list-item>
                <v-list-item-title>Download List 2</v-list-item-title>
            </v-list-item>
            <v-list-item>
                <v-list-item-title>Download List 4</v-list-item-title>
            </v-list-item>
        </v-list>
    </v-menu>
</template>

<script lang="ts">
import { CHECK_DOWNLOAD_STATUS } from "@/store/actions.type";

export default {
    name: "DownloadDropdown",
    props: {},
    computed: {
        downloadStarted() {
            return this.$store.getters.downloadStarted;
        },
        totalDownloadTasks():number {
            return this.$store.getters.downloadTotalTasks;
        },
        completedDownloadTasks():number {
            return this.$store.getters.downloadCompletedTasks;
        }
    },
    methods: {
        checkStatus() {
            this.$store.dispatch(CHECK_DOWNLOAD_STATUS);
            if (this.totalDownloadTasks > 0 && this.completedDownloadTasks == this.totalDownloadTasks) {
                clearInterval(this.intervalId);
                this.intervalId = null;
                console.log("Download Processing Complete: ", this.completedDownloadTasks, this.totalDownloadTasks);
            }
        }
    },
    watch: {
        downloadStarted(newval: boolean) {
            if (newval) {
                if (!this.intervalId) {
                    this.intervalId = window.setInterval(this.checkStatus, 3000); // Trigger every 3 second
                }
            } else {
                if (this.intervalId) {
                    clearInterval(this.intervalId);
                    this.intervalId = null;
                }
            }
        },
    },
    data() {
        return {
            intervalId: null as number | null, // Properly typed for TypeScript
        };
    },
    mounted() {
        // console.log(this.$store.getters.downloadStarted);
    },
    beforeUnmount() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
    },
};
</script>

<style scoped></style>