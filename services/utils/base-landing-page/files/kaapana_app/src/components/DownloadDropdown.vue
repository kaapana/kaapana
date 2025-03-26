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
                <v-list-item-title>
                    <a href="https://e230-pc25.inet.dkfz-heidelberg.de/kaapana-backend/get-static-website-results-html?object_name=downloads/download-selected-files-250319164821061096_25-03-19-17:48:38653660.zip" download>Download List</a>
                </v-list-item-title>
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
import Vue from "vue";
import { mapGetters } from "vuex";
import { CHECK_DOWNLOAD_STATUS } from "@/store/actions.type";

export default Vue.extend({
    name: "DownloadDropdown",
    props: {},
    data: () => ({
        intervalId: null as number | null, // Properly typed for TypeScript        
    }),
    computed: {
        downloadStarted(): boolean {
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
                this.resetInterval();
                console.log("Download Processing Complete: ", this.completedDownloadTasks, this.totalDownloadTasks);
            }
        },
        resetInterval() {
            if (this.intervalId) {
                clearInterval(this.intervalId);
                this.intervalId = null;
            }            
        }
    },
    watch: {
        downloadStarted(newval: boolean) {
            if (newval) {
                if (!this.intervalId) {
                    this.intervalId = window.setInterval(this.checkStatus, 5000); // Trigger every 3 second
                }
            } else {                
                this.resetInterval();                
            }
        },
    },
    mounted() {
        // console.log(this.$store.getters.downloadStarted);
    },
    beforeDestroy() {
        this.resetInterval();
    },
});
</script>

<style scoped></style>