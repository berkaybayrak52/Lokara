import { defineConfig } from 'vitest/config';
import path from 'node:path';

export default defineConfig({
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  // tsconfig sets `jsx: "preserve"` for Next's SWC pipeline, which uses the
  // automatic runtime. esbuild would otherwise fall back to the classic runtime
  // here and require `React` in scope, so a component that correctly omits the
  // import fails only under test.
  esbuild: { jsx: 'automatic' },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
  },
});
