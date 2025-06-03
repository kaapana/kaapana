<template>
    <div>
      <v-dialog v-model="dialog" width="50vw">
        <template v-slot:activator="{ on, attrs }">
          <v-btn icon v-bind="attrs" v-on="on" title="About Platform">
            <v-icon>mdi-information-outline</v-icon>
          </v-btn>
        </template>

        <v-card>
            <v-container fluid>
              <v-card-title class="text-h5">
                About Kaapana Platform
              </v-card-title>
              <v-card-text class="pt-2 pb-8">
                <div class="text-h6">
                  Important Links
                </div>
                <div class="py-2">
                  <v-btn
                    text target="_blank"
                    href="https://join.slack.com/t/kaapana/shared_invite/zt-hilvek0w-ucabihas~jn9PDAM0O3gVQ/"
                  >
                    Join Slack
                    <v-icon right>mdi-slack</v-icon>
                  </v-btn>
                  <v-btn
                    text target="_blank"
                    href="https://codebase.helmholtz.cloud/kaapana/kaapana/-/issues"
                  >
                    Report Issue
                    <v-icon right>mdi-open-in-new</v-icon>
                  </v-btn>
                  <v-btn
                    text target="_blank"
                    href="/docs/faq_root.html"
                  >
                    More Details
                    <v-icon right>mdi-frequently-asked-questions</v-icon>
                  </v-btn>
                </div>
                <div class="text-h6 py-4">
                  Version Information
                </div>
                <v-row v-for="(value, key) in versionObj" :key="key">
                    <v-col cols="3" class="py-2"><b>{{ key }}:</b></v-col>
                    <v-col class="py-2">{{ value }}</v-col>
                </v-row>
              </v-card-text>

              <v-card-actions>
                &copy; DKFZ 2018 - DKFZ 2025
              </v-card-actions>
            </v-container>
        </v-card>
      </v-dialog>
    </div>
  </template>



  <script>
  import { mapGetters } from "vuex";

  export default {
    data: () => ({
      dialog: false,
      versionObj: {},
    }),
    components: {
    },
    created() {

    },
    computed: {
      ...mapGetters([
        "commonData",
      ]),
    },
    created() {
      this.versionObj['Repository URL'] = 'https://codebase.helmholtz.cloud/kaapana/kaapana';
      this.formatVersions(this.commonData.version);
    },
    methods: {
      formatVersions(versionText) {
        if (!versionText) {
          return;
        }

        let splitted = versionText.split('|');
        splitted.forEach((versionItem) => {
          let versionItemCleaned = versionItem.trim();
          let keyEndPos = versionItemCleaned.indexOf(':')
          const versionItemKey = versionItemCleaned.substr(0, keyEndPos);
          const versionItemVal = versionItemCleaned.substr(keyEndPos+1);
          this.versionObj[versionItemKey] = versionItemVal.trim();
        })
      }
    },
    watch: {
      commonData(newCommondata) {
        if (newCommondata) {
          this.formatVersions(newCommondata.version);
        }
      }
    },
  };
  </script>

  <style lang="scss" scoped>

  </style>

  <style>

  </style>
