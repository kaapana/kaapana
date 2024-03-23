<template>
    <div>
        <!-- <div>Idle: <b>{{ isIdle }}</b></div>
        <div>Inactive: <b class="text-primary">{{ idledFor }}s</b></div> -->
    </div>
</template>

<script lang="ts">
import Vue from 'vue'
import { useIdle } from '@vueuse/core'

export default Vue.extend({
    computed: {
        isIdle() {
            return this.$store.state.idle.isIdle
        },
    },
    mounted() {
        const { idle } = useIdle(30000)

        idle.value = false

        this.$watch(() => idle.value, (newValue, oldValue) => {
            if (newValue) {
                console.log("Got emitted")
                this.$store.commit('setIsIdle', true) // Dispatch action to set idle state to true
            } else {
                console.log("Not Idle")
                this.$store.commit('setIsIdle', false) // Dispatch action to set idle state to false
            }
        })
    }
})
</script>