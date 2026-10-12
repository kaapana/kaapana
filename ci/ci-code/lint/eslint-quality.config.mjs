import js from '@eslint/js'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginVitest from '@vitest/eslint-plugin'
import pluginPlaywright from 'eslint-plugin-playwright'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'
import { setup } from '../../../eslint.config.mjs'

export default defineConfigWithVueTs(
  ...setup,
  // ESLint recommended: likely bugs, such as undefined variables, unreachable code or duplicate keys
  js.configs.recommended,
  // Vue recommended: essential plus readability and consistency, such as prop definitions and attribute order
  pluginVue.configs['flat/recommended'],
  // typescript-eslint recommended: TypeScript bugs and bad practice, such as any, unused variables or ts-ignore
  vueTsConfigs.recommended,

  {
    name: 'kaapana/quality',
    rules: {
      // v-slot must be valid; modifiers are allowed because Vuetify uses slot names like item.name
      'vue/valid-v-slot': ['error', { allowModifiers: true }],
    },
  },

  // Vitest recommended for unit tests: misplaced expect, disabled or focused tests, duplicate titles
  {
    ...pluginVitest.configs.recommended,
    files: ['**/src/**/__tests__/*'],
  },

  // Playwright recommended for end-to-end tests: missing await, fixed timeouts, focused or skipped tests
  {
    ...pluginPlaywright.configs['flat/recommended'],
    files: ['**/e2e/**/*.{test,spec}.ts', 'tests/ui/**/*.ts'],
  },

  // turns off every rule that Prettier already handles
  skipFormatting,
)
