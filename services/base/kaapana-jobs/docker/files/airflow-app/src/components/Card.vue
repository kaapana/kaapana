<template>
  <div>
    <b-col>
      <b-card
      :title="name"
      img-src="https://images.pexels.com/photos/3617500/pexels-photo-3617500.jpeg?cs=srgb&dl=pexels-benjamin-suter-3617500.jpg&fm=jpg"
      img-alt="Card-Info"
      img-top
      tag="article"
      style="max-width:20em"
      class="mb-2"
      footer="Card-Footer"
      >
        <b-card-text>
            Lorem ipsum dolor sit amet consectetur adipisicing elit.
             Voluptatem, necessitatibus laboriosam fuga eaque voluptatum unde
              quidem saepe soluta distinctio molestias eum fugit alias iure
               perspiciatis eveniet veritatis obcaecati? Nisi, porro!
        </b-card-text>
        <b-button variant="primary">Apply</b-button>
      </b-card>
    </b-col>
  </div>
</template>

<script>
import Vue from 'vue';

export default Vue.extend({
  props: ['name'],
});
</script>

<style lang="stylus" scoped>

</style>
