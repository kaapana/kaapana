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
        const idleTime = parseInt(process.env.VUE_APP_IDLE_TIMEOUT as string, 10);
        const { idle } = useIdle(idleTime);

        idle.value = false

        this.$watch(() => idle.value, (newValue, oldValue) => {
            if (newValue) {
                console.log("Got emitted")
                this.$store.commit('setIsIdle', true)
            } else {
                console.log("Not Idle")
                this.$store.commit('setIsIdle', false)
            }
        })
    }
})
</script>