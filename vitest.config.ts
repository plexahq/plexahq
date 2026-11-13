import { defineConfig } from "vitest/config";

// Separate from vite.config.ts, whose root is the website in site/.
export default defineConfig({
  test: {
    include: ["test/**/*.test.ts"],
  },
});
