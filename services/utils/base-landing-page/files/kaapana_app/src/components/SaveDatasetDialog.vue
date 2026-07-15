<template>
  <div>
    <v-dialog
        v-model="show"
        width="500"
    >
      <v-card>
        <v-card-title>
          Save Dataset
        </v-card-title>
        <v-card-text>
          <v-text-field
              v-model="name"
              label="Name"
              clearable
          ></v-text-field>
          <v-select
              v-model="access_level"
              label="Access Level"
              default="private"
              :items="['private', 'project']"
          ></v-select>
        </v-card-text>
        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click.stop="save" :disabled="name === ''">Save</v-btn>
          <v-btn @click.stop="show=false">Cancel</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
<script>

export default {
  props: {
    value: Boolean
  },
  data: () => ({
    name: "",
    access_level: "private"
  }),
  methods: {
    save() {
      this.$emit('save', this.name, this.access_level)
      this.name = ""
      this.access_level = "private"
    }
  },
  computed: {
    show: {
      get() {
        return this.value
      },
      set(value) {
        this.name = ""
        this.access_level = "private"
        this.$emit('cancel', value)
      }
    }
  }
}
</script>

<style scoped>

</style>