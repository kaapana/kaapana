import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginVitest from '@vitest/eslint-plugin'
import pluginPlaywright from 'eslint-plugin-playwright'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'
import { setup } from '../eslint.config.mjs'

export default defineConfigWithVueTs(
  ...setup,
  pluginVue.configs['flat/essential'],
  vueTsConfigs.recommended,

  {
    name: 'kaapana/quality',
    rules: {
      'vue/valid-v-slot': ['error', { allowModifiers: true }],
    },
  },

  {
    ...pluginVitest.configs.recommended,
    files: ['**/src/**/__tests__/*'],
  },

  {
    ...pluginPlaywright.configs['flat/recommended'],
    files: ['**/e2e/**/*.{test,spec}.ts', 'tests/ui/**/*.ts'],
  },

  skipFormatting,
)
