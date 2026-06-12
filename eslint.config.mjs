import antfu from '@antfu/eslint-config'
import js from '@eslint/js'
import eslintConfigPrettier from 'eslint-config-prettier/flat'
import globals from 'globals'

const ignores = ['node_modules', '**/tailwind.css', 'frontend/static/js/libraries', '.vscode']

export default antfu(
  {
    ignores,
    gitignore: true,
    stylistic: {
      indent: 4,
    },
    rules: {
      "no-console": "off"
    }
  },
  [
    {
      ignores,
    },
    { files: ['**/*.{js,mjs,cjs}'], plugins: { js }, extends: ['js/recommended'], languageOptions: { globals: globals.browser } },
    eslintConfigPrettier,
  ]
)
