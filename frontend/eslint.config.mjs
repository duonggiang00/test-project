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
            "message": "❌ ANTI-PATTERN: TUYỆT ĐỐI CẤM gọi API trực tiếp. Hãy dùng custom hook (SWR) trong src/hooks/"
          },
          {
            "name": "axios",
            "message": "❌ ANTI-PATTERN: Cấm dùng axios trong giao diện. Mọi request phải thông qua src/hooks/ hoặc src/lib/api.ts"
          }
        ],
        "patterns": [{
          "group": ["**/lib/api"],
          "message": "❌ ANTI-PATTERN: TUYỆT ĐỐI CẤM gọi API trực tiếp. Hãy dùng custom hook (SWR) trong src/hooks/"
        }]
      }]
    }
  }
  ,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
