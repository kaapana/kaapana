<script setup lang="ts">
import type { SecurityNotification } from '@/types/misc';
import { defineComponent, type PropType } from 'vue';
import Group, { EGroupPadding } from './Group.vue';
</script>

<template>
  <div class="notification-container">
    <template v-for="notification in notifications">
      <Group :paddingSize=EGroupPadding.SMALL class="notification">
        <div>🔔 <strong>{{ notification.title }}</strong></div>
        <div v-if="notification.description">{{ notification.description }}</div>
        <a v-if="notification.link" :href="notification.link">{{ notification.link }}</a>
      </Group>
    </template>
  </div>
</template>

<script lang="ts">
export default defineComponent({
  props: {
    notifications: {
      type: Array as PropType<SecurityNotification[]>,
      required: true
    }
  },
  computed: {
    display() {
      return this.notifications.length > 0 ? 'flex' : 'none';
    }
  }
});
</script>

<style scoped>
.notification-container {
  position: fixed;
  right: 0px;
  top: var(--default-margin-value);
  width: max-content;
  max-width: 380px;
  min-width: 230px;
  max-height: calc(100vh - 2*var(--default-margin-value));
  display: v-bind(display);
  flex-direction: column;
  gap: 10px;
  overflow-y: scroll;
  transform: translate(70%, 0px);
  transition: all .15s ease-out;
  mask-image: linear-gradient(to right, rgba(0,0,0,1), rgba(0,0,0,1) 15%, rgba(0,0,0,0) 60%);
  padding: 5px;
  padding-right: var(--default-padding-value);
}

.notification-container:hover {
  transform: translate(0px, 0px);
  mask-image: linear-gradient(to right, rgba(0,0,0,1), rgba(0,0,0, 1) 100%);
}

.notification {
  display: flex;
  flex-direction: column;
  box-shadow: -3px 3px 3px rgba(0,0,0,0.5);
}

</style>