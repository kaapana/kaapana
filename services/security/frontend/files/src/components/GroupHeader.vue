<script setup lang="ts">
import { defineComponent, type PropType } from 'vue';
import Divider from '@/components/Divider.vue';
import Header, { EHeaderSize } from "@/components/Header.vue";
import ElementList, { EElementListMargin } from '@/components/ElementList.vue';
import { EDirection } from '@/types/enums';
import type { RouteParams } from 'vue-router';
import { navigateTo } from '@/router';
</script>

<template>
  <div class="header-breadcrumb-container">
    <Header :title="title" :size=EHeaderSize.NORMAL></Header>
    <div class="breadcrumbs" v-if="breadCrumbs !== undefined">
      <template v-for="[index, breadCrumb] of breadCrumbs.entries()">
        <div v-if="index !== 0" >></div>
        <div :class="breadCrumbClasses(breadCrumb.underlined, !!breadCrumb.routerLink)" @click="clickOnBreadCrumb(breadCrumb.routerLink);">{{ breadCrumb.name }}</div>
      </template>
    </div>
  </div>
  <ElementList class="secondary-information" :direction=EDirection.HORIZONTAL :margin=EElementListMargin.NORMAL>
    <slot></slot>
  </ElementList>
  <Divider v-if="divider"></Divider>
</template>

<script lang="ts">
interface BreadCrumbRouterLink {
  name: string;
    params: RouteParams;
}
export interface BreadCrumb {
  name: string;
  underlined: boolean;
  routerLink?: BreadCrumbRouterLink;
}

export default defineComponent({
  props: {
    title: {
      type: String,
      required: true
    },
    divider: Boolean,
    breadCrumbs: {
      type: Array as PropType<BreadCrumb[]>,
      required: false
    }
  },
  methods: {
    clickOnBreadCrumb(routerLink?: BreadCrumbRouterLink) {
      if (!routerLink) {
        return;
      }

      navigateTo(routerLink.name, routerLink.params);
    },
    breadCrumbClasses(underlined: boolean, isLink:boolean) {
      const classes:string[] = [];
      if (underlined) {
        classes.push("underlined")
      }
      if (isLink) {
        classes.push("link");
      }
      return classes.join(" ");
    }
  }
});
</script>

<style scoped>
.secondary-information {
  font-size: 80%;
  margin-top: calc(var(--default-margin-value) / 2);
}

.underlined {
  text-decoration: underline;
}

.link {
  cursor: pointer;
}

.breadcrumbs {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 5px;
}

.breadcrumbs > * {
  font-weight: 400;
  font-size: 70%;
}

.header-breadcrumb-container {
  display: flex;
  flex-direction: column;
}

@media (min-width: 1024px) {
  .header-breadcrumb-container {
    flex-direction: row;
  }
}
</style>