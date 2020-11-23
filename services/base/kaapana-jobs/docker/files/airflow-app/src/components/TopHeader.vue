<template>
  <div>
    <b-navbar toggleable="lg" type="dark" variant="info">
    <b-navbar-brand>
    <img
    to="/"
    src="https://sdtimes.com/wp-content/uploads/2019/01/pin_large-490x490.png"
    alt="Airflow"
    width="40"
    >
    <font size="5">Airflow </font><font size="3">by Kaapana</font>
    </b-navbar-brand>

    <b-navbar-toggle target="nav-collapse"></b-navbar-toggle>

    <b-collapse id="nav-collapse" is-nav>
      <b-navbar-nav>
        <b-nav-item to="/">Home</b-nav-item>
        <b-nav-item to="/about">About</b-nav-item>
      </b-navbar-nav>

      <!-- Right aligned nav items -->
      <b-navbar-nav class="ml-auto">
        <b-nav-form>
          <b-form-input size="sm" class="mr-sm-2" placeholder="Search"></b-form-input>
          <b-button size="sm" class="my-2 my-sm-0" type="submit">Search</b-button>
        </b-nav-form>
      </b-navbar-nav>
    </b-collapse>
  </b-navbar>
  </div>
</template>

<script lang="ts">
import Vue from 'vue';

export default Vue.extend({
});
</script>

<style lang="scss" scoped>
#nav a.router-link-exact-active {
    color: white;
}
.bg-info {
    background-color: #005a63 !important;
}
#nav a {
    color: white;
}
b-nav-item-dropdown {
    color: white;
}
</style>
