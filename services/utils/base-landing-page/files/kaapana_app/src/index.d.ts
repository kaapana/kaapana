declare module 'idle-vue' {
    import Vue, { PluginFunction } from 'vue'
    export interface IdleVueUseOptions {
      events?: string[]
      eventEmitter?: any
      idleTime?: number
      keepTracking?: boolean
      moduleName?: string
      startAtIdle?: boolean
      store?: any
    }
    module "vue/types/vue" {
      interface Vue {
        isAppIdle: boolean
      }
    }
   // In case you want to vue.extend format
    module "vue/types/options" {
      interface ComponentOptions<V extends Vue> {
        onIdle?: () => void
        onActive?: () => void
      }
    }
    export function install(): PluginFunction<IdleVueUseOptions>
  }