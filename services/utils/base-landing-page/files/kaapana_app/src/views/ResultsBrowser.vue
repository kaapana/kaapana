<template lang="pug">
v-container(text-left fluid)
  IdleTracker
  v-row
    v-col(cols="3")
      v-card
        v-text-field(v-model='search' label='Search loaded results' hint='Search only filters folders and files that have already been loaded.' persistent-hint flat hide-details='auto' solo clearable clear-icon='mdi-close-circle-outline')
        v-treeview(v-model="tree" :items="staticUrls" :search="search" item-key="path" selectable return-object activatable open-on-click :load-children="fetchChildren")
          template(v-slot:prepend='{ item, open }')
            v-icon(v-if='!item.file')
              | {{ open ? 'mdi-folder-open' : 'mdi-folder' }}
            v-icon(v-else)
              | {{ files[item.file] }}
          template(v-slot:label='{ item }')
            span(class="text-wrap") {{item.name}}
          template(v-slot:append='{ item }')
            v-btn(v-if='!item.file && item.nextContinuationToken' x-small text color='primary' :loading='item.loadingMore' @click.stop='loadMoreForNode(item)') Load more
        v-card-actions(v-if='rootNextContinuationToken')
          v-btn(text color='primary' :loading='rootLoadingMore' @click='loadMoreRootResults') Load more root results

    v-col(cols="9")
      div(v-if="selectedFiles.length == 0")
        h1 Workflow results 
        p Results from the workflows will be shown here!
        v-icon(class="results-icon") mdi-chart-bar-stacked
      v-expansion-panels(v-model="panel" accordion)
        v-expansion-panel(v-for="node in selectedFiles" :key="node.path")
          v-expansion-panel-header
            span {{ node.name }}
              v-tooltip(bottom='')
                template(v-slot:activator='{ on, attrs }')
                  v-icon(color='primary' dark='' v-bind='attrs' v-on='on')
                    | mdi-folder
                span {{ node.url }}
              v-icon(@click="openExternalPage(node.url)" color="primary") mdi-open-in-new
          v-expansion-panel-content
            IFrameWindow(ref="foo" :iFrameUrl="node.url" width="100%" height="100%")
  
</template>


<script>
// @ is an alias to /src
import Vue from 'vue'
import { mapGetters } from "vuex";
import kaapanaApiService from "@/common/kaapanaApi.service";

import IFrameWindow from "@/components/IFrameWindow.vue";
import IdleTracker from "@/components/IdleTracker.vue";
export default {
  name: 'iframe-view',
  components: {
    IFrameWindow,
    IdleTracker,
  },
  data: function () {
    return {
      panel: null,
      staticUrls: [],
      rootNextContinuationToken: null,
      rootLoadingMore: false,
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
    ...mapGetters(["currentUser", "isAuthenticated", "externalWebpages"]),
    selectedFiles() {
      return this.tree.filter((item) => item.file && item.url)
    }
  },
  mounted() {
    this.getStaticWebsiteResults()
  },
  watch: {
    selectedFiles(newValue) {
      if (newValue.length > 0) {
        this.panel = newValue.length - 1
      }
    }
  },
  methods: {
    getStaticWebsiteResults() {
      kaapanaApiService
        .kaapanaApiGet("/get-static-website-results-tree")
        .then((response) => {
          const payload = response.data || { items: [], nextContinuationToken: null };
          this.staticUrls = payload.items || [];
          this.rootNextContinuationToken = payload.nextContinuationToken || null;
        })
        .catch((err) => {
          this.staticUrls = []
          this.rootNextContinuationToken = null;
        });
    },
    async fetchChildren(item) {
      if (item.file || item.childrenLoaded) {
        return;
      }

      try {
        const response = await kaapanaApiService.kaapanaApiGet(
          "/get-static-website-results-tree",
          { prefix: item.path }
        );
        const payload = response.data || { items: [], nextContinuationToken: null };
        this.$set(item, 'children', payload.items || []);
        this.$set(item, 'nextContinuationToken', payload.nextContinuationToken || null);
        this.$set(item, 'childrenLoaded', true);
      } catch (error) {
        this.$set(item, 'children', []);
        this.$set(item, 'nextContinuationToken', null);
        this.$set(item, 'childrenLoaded', true);
      }
    },
    async loadMoreForNode(item) {
      if (!item.nextContinuationToken) {
        return;
      }

      this.$set(item, 'loadingMore', true);
      try {
        const response = await kaapanaApiService.kaapanaApiGet(
          "/get-static-website-results-tree",
          {
            prefix: item.path,
            continuation_token: item.nextContinuationToken,
          }
        );
        const payload = response.data || { items: [], nextContinuationToken: null };
        const children = (item.children || []).concat(payload.items || []);
        this.$set(item, 'children', children);
        this.$set(item, 'nextContinuationToken', payload.nextContinuationToken || null);
      } catch (error) {
        console.error('Failed to load more workflow result children:', error);
      } finally {
        this.$set(item, 'loadingMore', false);
      }
    },
    async loadMoreRootResults() {
      if (!this.rootNextContinuationToken) {
        return;
      }

      this.rootLoadingMore = true;
      try {
        const response = await kaapanaApiService.kaapanaApiGet(
          "/get-static-website-results-tree",
          { continuation_token: this.rootNextContinuationToken }
        );
        const payload = response.data || { items: [], nextContinuationToken: null };
        this.staticUrls = this.staticUrls.concat(payload.items || []);
        this.rootNextContinuationToken = payload.nextContinuationToken || null;
      } catch (error) {
        console.error('Failed to load more root workflow results:', error);
      } finally {
        this.rootLoadingMore = false;
      }
    },
    openExternalPage(url) {
      window.open(url, '_blank');
    },
  }
}
</script>

<style lang="scss">
.v-treeview-node__content,
.v-treeview-node__label {
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
