import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-unused-vars": "error",
      "react-hooks/exhaustive-deps": "error",
      "prefer-const": "error",
      "no-console": ["warn", { "allow": ["warn", "error"] }]
    }
  },
  {
    files: ["src/app/**/*.{ts,tsx}", "src/components/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", {
        "paths": [
          {
            "name": "@/lib/api",
            "message": "ANTI-PATTERN: Do not call the backend API directly. Use an SWR hook from src/hooks/."
          },
          {
            "name": "axios",
            "message": "ANTI-PATTERN: Do not use axios in UI components. Route requests through src/hooks/ or the approved service boundary."
          }
        ],
        "patterns": [{
          "group": ["**/lib/api"],
          "message": "ANTI-PATTERN: Do not call the backend API directly. Use an SWR hook from src/hooks/."
        }]
      }]
    }
  }
  ,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    ".next-e2e-mocked/**",
    ".next-e2e-real/**",
    "out/**",
    "build/**",
    "reports/**",
    "coverage/**",
    "playwright-report/**",
    "test-results/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
