<script setup lang="ts">
import { defineComponent } from 'vue'
import { RouterLink, RouterView } from "vue-router";
import HelloWorld from './components/HelloWorld.vue';
import { DARK_MODE_ACTIVE, DARK_MODE_NOT_ACTIVE, QUERY_DARK_MODE } from './stores/messages.types';
</script>

<template>
  <header>
    <!-- <img
      alt="Vue logo"
      class="logo"
      src="@/assets/logo.svg"
      width="125"
      height="125"
    /> -->

    <div class="wrapper">
      <HelloWorld msg="Security" />

      <!-- <nav>
        <RouterLink to="/">Home</RouterLink>
        <RouterLink to="/configuration">Configuration</RouterLink>
      </nav> -->
      <p>Darkmode activated: {{ darkMode }}</p>
      <p v-if="wazuhAgentAvailable===null">Loading Wazuh agents</p>
      <pre v-else>Wazuh agent available: {{ wazuhAgentAvailable }}</pre>
    </div>
  </header>

  <RouterView />
</template>

<script lang="ts">
export default defineComponent({
  data() {
    return {
      darkMode: false,
      wazuhAgentAvailable: null
    };
  },
  methods: {
    async checkWazuhAgents() {
      const response = await fetch(window.location.origin + "/security/api/extension/wazuh/agent-installed");
      const json = await response.json();
      this.wazuhAgentAvailable = json["agent_installed"];
    },
    receiveMessage(event: MessageEvent) {
      console.log(event);

      // only process our own messages
      if (event.origin !== window.location.origin || !("message" in event.data)) {
        return;
      }
      if (event.data.message === DARK_MODE_ACTIVE) {
        this.darkMode = true;
      } else if (event.data.message === DARK_MODE_NOT_ACTIVE) {
        this.darkMode = false;
      }
    }
  },
  created() {
    window.addEventListener("message", this.receiveMessage);

    if (window.parent) {
      window.parent.postMessage({message: QUERY_DARK_MODE}, "*");
    }
  },
  beforeDestroy() {
    window.removeEventListener("message", this.receiveMessage);
  },
  mounted() {
    this.checkWazuhAgents();
  }
});
</script>

<style scoped>
header {
  line-height: 1.5;
}

.wrapper {
  width: 100%;
}

/* .logo {
  display: block;
  margin: 0 auto 2rem;
}

nav {
  width: 100%;
  font-size: 12px;
  text-align: center;
  margin-top: 2rem;
} */

/* nav a.router-link-exact-active {
  color: var(--color-text);
}

nav a.router-link-exact-active:hover {
  background-color: transparent;
}

nav a {
  display: inline-block;
  padding: 0 1rem;
  border-left: 1px solid var(--color-border);
}

nav a:first-of-type {
  border: 0;
} */

@media (min-width: 1024px) {
  header {
    display: flex;
    place-items: center;
    padding-right: calc(var(--section-gap) / 2);
  }

  /* .logo {
    margin: 0 2rem 0 0;
  } */

  header .wrapper {
    display: flex;
    place-items: flex-start;
    flex-wrap: wrap;
  }

  /* nav {
    text-align: left;
    margin-left: -1rem;
    font-size: 1rem;

    padding: 1rem 0;
    margin-top: 1rem;
  } */
}
</style>
