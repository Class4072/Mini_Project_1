import js from "@eslint/js";
import prettier from "eslint-config-prettier";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import { defineConfig, globalIgnores } from "eslint/config";
import globals from "globals";

export default defineConfig([
  globalIgnores(["dist", "coverage"]),
  {
    files: ["**/*.{js,jsx}"],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      "no-unused-vars": ["error", { varsIgnorePattern: "^[A-Z_]" }],
    },
  },
  {
    // src 에서는 console 대신 src/utils/logger.js 를 쓴다.
    files: ["src/**/*.{js,jsx}"],
    rules: { "no-console": "error" },
  },
  {
    files: ["src/utils/logger.js", "**/*.test.{js,jsx}"],
    rules: { "no-console": "off" },
  },
  {
    files: ["**/*.test.{js,jsx}", "jest.setup.js", "**/__mocks__/**", "test/**"],
    languageOptions: { globals: { ...globals.browser, ...globals.jest } },
  },
  {
    files: ["*.cjs"],
    languageOptions: { sourceType: "commonjs", globals: globals.node },
  },
  {
    files: ["vite.config.js", "jest.config.js", "eslint.config.js"],
    languageOptions: { globals: globals.node },
  },
  prettier,
]);
