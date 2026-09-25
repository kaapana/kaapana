import { globalIgnores } from 'eslint/config'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'

export const setup = [
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
    'services/kaapana-admin/maintenance-page/**',
  ]),

  vueTsConfigs.base,
]

const enforced = {
  name: 'kaapana/enforced',
  linterOptions: {
    reportUnusedDisableDirectives: 'off',
  },
  rules: {
    'vue/block-lang': 'off',
    'vue/valid-v-slot': ['error', { allowModifiers: true }],
    'vue/multi-word-component-names': 'off',
    'vue/no-unused-components': 'off',
    'vue/no-unused-vars': 'off',
    'no-debugger': 'error',
    'no-dupe-else-if': 'error',
    'no-duplicate-case': 'error',
    'no-self-assign': 'error',
    'no-unsafe-finally': 'error',
    'use-isnan': 'error',
    'valid-typeof': 'error',
  },
}

export default defineConfigWithVueTs(
  ...setup,
  pluginVue.configs['flat/essential'],
  enforced,
  skipFormatting,
)
