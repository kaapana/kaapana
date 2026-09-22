import { globalIgnores } from 'eslint/config'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginVitest from '@vitest/eslint-plugin'
import pluginPlaywright from 'eslint-plugin-playwright'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'

export default defineConfigWithVueTs(
  {
    name: 'kaapana/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue}'],
  },

  globalIgnores([
    '**/*.{js,cjs,mjs,jsx}',
    '**/node_modules/**',
    '**/.venv/**',
    '**/test-results/**',
    '**/dist/**',
    '**/dist-ssr/**',
    '**/coverage/**',
    'build/**',
    'docs/build/**',
    '**/components.d.ts',
    '**/typed-router.d.ts',
    '**/auto-imports.d.ts',
    'services/meta/os-dashboards/**',
  ]),

  pluginVue.configs['flat/essential'],
  vueTsConfigs.recommended,

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
