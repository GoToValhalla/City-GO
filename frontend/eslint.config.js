import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

const legacySyncRules = {
  'react-hooks/set-state-in-effect': 'off',
}

const testFileRules = {
  '@typescript-eslint/no-unused-vars': 'off',
  'react-hooks/set-state-in-effect': 'off',
  'react-refresh/only-export-components': 'off',
}

export default defineConfig([
  globalIgnores([
    'dist',
    'src/pages/admin/AdminCoverageGapsPage.tsx',
    'src/pages/admin/AdminCoverageGapsSnapshotPage.tsx',
  ]),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [js.configs.recommended, tseslint.configs.recommended, reactHooks.configs.flat.recommended, reactRefresh.configs.vite],
    languageOptions: { ecmaVersion: 2020, globals: { ...globals.browser, ...globals.node } },
  },
  {
    files: ['**/*.test.{ts,tsx}'],
    rules: testFileRules,
  },
  {
    files: ['src/features/city-routing/CityRouteScope.tsx'],
    rules: legacySyncRules,
  },
  {
    files: ['src/pages/admin/AdminDataPipelinePage.tsx'],
    rules: legacySyncRules,
  },
  {
    files: ['src/pages/places/PlacesListPage.tsx'],
    rules: legacySyncRules,
  },
  {
    files: ['src/pages/admin/AdminImportJobsPage.tsx'],
    rules: {
      'react-hooks/exhaustive-deps': 'off',
      'react-hooks/set-state-in-effect': 'off',
      'react-refresh/only-export-components': 'off',
    },
  },
  {
    files: ['src/pages/admin/AdminTaxonomyPage.tsx'],
    rules: {
      'react-hooks/exhaustive-deps': 'off',
      'react-hooks/set-state-in-effect': 'off',
      'react-refresh/only-export-components': 'off',
    },
  },
])
