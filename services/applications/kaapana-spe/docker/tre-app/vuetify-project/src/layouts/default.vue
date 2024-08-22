<template>
  <v-app>
    <!-- Navigation Drawer -->
    <v-navigation-drawer app permanent>
      <v-list>
        <v-list-item
          v-for="(item, index) in menuItems"
          :key="index"
          :to="item.route"
          router
          link
        >
          <v-list-item-icon>
            <v-icon>{{ item.icon }}</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            <v-list-item-title>{{ item.title }}</v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-main>
      <router-view />
    </v-main>

    
  </v-app>
</template>

<script>
export default {
  data() {
    return {
      menuItems: [
        { title: "Home", route: "/TreBase" },
        { title: "User view", route: "/TreUserOverview" },
        { title: "Admin view", route: "/TreAdminOverview" },
      ],
    };
  },
};
</script>

<style scoped>
.v-application {
  font-family: 'Roboto', sans-serif;
}

.v-main {
  padding-left: 256px; 
}

.v-navigation-drawer {
  width: 256px;
}
</style>
