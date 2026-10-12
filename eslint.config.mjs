import { globalIgnores } from 'eslint/config'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'
import globals from 'globals'

export const setup = [
  {
    name: 'kaapana/files-to-lint',
    files: ['**/*.{js,mjs,cjs,jsx,ts,mts,tsx,vue}'],
  },

  globalIgnores([
    '**/*.min.js',
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
    'services/kaapana-admin/maintenance-page/**',
  ]),

  {
    name: 'kaapana/javascript-globals',
    files: ['**/*.{js,mjs,cjs,jsx}'],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
  },

  // TypeScript parser for .ts files and <script lang="ts"> in .vue files, no rules
  vueTsConfigs.base,
]

const enforced = {
  name: 'kaapana/enforced',
  rules: {
    // v-slot must be valid; modifiers are allowed because Vuetify uses slot names like item.name
    'vue/valid-v-slot': ['error', { allowModifiers: true }],
  },
}

export default defineConfigWithVueTs(
  ...setup,
  // Vue essential: templates and components that are invalid or break at runtime
  pluginVue.configs['flat/essential'],
  enforced,
  // turns off every rule that Prettier already handles
  skipFormatting,
)
