
<template lang="pug">
  v-container(text-left)
    v-row
      v-col(cols="3")
        v-card
          v-text-field(v-model='search' label='Search directories'  flat hide-details solo clearable clear-icon='mdi-close-circle-outline')
          v-treeview(v-model="tree" :items="staticUrls" :search="search" item-key="path" selectable return-object activatable open-on-click)
            template(v-slot:prepend='{ item, open }')
              v-icon(v-if='!item.file')
                | {{ open ? 'mdi-folder-open' : 'mdi-folder' }}
              v-icon(v-else)
                | {{ files[item.file] }}
            template(v-slot:label='{ item }')
              span(class="text-wrap") {{item.name}}

      v-col(cols="9")
        div(v-if="this.tree.length == 0")
          h1 Workflow results 
          p Results from the workflows will be shown here!
          v-icon(class="results-icon") mdi-chart-bar-stacked
        v-expansion-panels(v-model="panel" accordion)
          v-expansion-panel(v-for="node in tree" :key="node.path")
            v-expansion-panel-header
              span {{ node.name }}
                v-tooltip(bottom='')
                  template(v-slot:activator='{ on, attrs }')
                    v-icon(color='primary' dark='' v-bind='attrs' v-on='on')
                      | mdi-folder
                  span {{ node.path }}
                v-icon(@click="openExternalPage(node.path)" color="primary") mdi-open-in-new
            v-expansion-panel-content
              IFrameWindow(ref="foo" :iFrameUrl="node.path" width="100%" height="100%")
    
</template>


<script>
// @ is an alias to /src
import Vue from 'vue'
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

import IFrameWindow from "@/components/IFrameWindow.vue";
export default {
  name: 'iframe-view',
  components: {
    IFrameWindow
  },
  data: function () {
    return {
      iFrameUrl: null,
      panel: null,
      staticUrls: [],
      search: null,
      files: {
        html: 'mdi-language-html5',
        js: 'mdi-nodejs',
        json: 'mdi-code-json',
        md: 'mdi-language-markdown',
        pdf: 'mdi-file-pdf',
        png: 'mdi-file-image',
        txt: 'mdi-file-document-outline',
        xls: 'mdi-file-excel',
      },
      tree: [],
    }
  },
  computed: {
    ...mapGetters(["currentUser", "isAuthenticated", "externalWebpages"])
  },
  mounted () {
    this.getStaticWebsiteResults()
  },
  watch:{
    tree(newValue) {
      if (newValue.length > 0 ) {
        this.panel = newValue.length-1
      }
    }
  },
  methods: {
    getStaticWebsiteResults() {
      kaapanaApiService
        .kaapanaApiGet("/get-static-website-results")
        .then((response) => {
          this.staticUrls = response.data;
        })
        .catch((err) => {
          this.staticUrls = []
        });
    },
    openExternalPage(url) {
      window.open(url, '_blank');
    },
  }
}
</script>

<style lang="scss">
.v-treeview-node__content, .v-treeview-node__label {
  flex-shrink: 1;
}
.v-treeview-node__root {
  height: auto;
}

.results-icon {
  font-size: 425px !important;
  text-align: center;
  width: 100%;
}
</style>
