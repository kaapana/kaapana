<template>
    <div>
        <div>Idle: <b>{{ isIdle }}</b></div>
        <div>Inactive: <b class="text-primary">{{ idledFor }}s</b></div>
    </div>
</template>

<script lang="ts">
import Vue from 'vue'
import { useIdle, useTimestamp } from '@vueuse/core'

export default Vue.extend({
    computed: {
        isIdle() {
            return this.$store.state.idle.isIdle
        },
        idledFor() {
            return this.$store.state.idle.idledFor
        }
    },
    mounted() {
        const { idle, lastActive } = useIdle(5000)
        const now = useTimestamp({ interval: 1000 })

        idle.value = false

        this.$watch(() => idle.value, (newValue, oldValue) => {
            if (newValue) {
                console.log("Got emitted")
                this.$store.commit('setIdle', true) // Dispatch action to set idle state to true
            } else {
                console.log("Not Idle")
                this.$store.commit('setIdle', false) // Dispatch action to set idle state to false
            }
        })

        // Update the counted seconds of inactivity every second
        setInterval(() => {
            this.$store.commit('setIdledFor', Math.floor((now.value - lastActive.value) / 1000)) // Dispatch action to update idledFor value
        }, 1000)
    }
})
</script>