import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary'],
      include: [
        'src/main/portable-vault.ts',
        'src/main/report-renderer.ts',
        'src/shared/model-registry.ts',
        'src/shared/report-templates.ts',
        'src/shared/sample-corpus-schema.ts',
        'src/renderer/components/FeatureCard.vue',
      ],
      thresholds: {
        lines: 70,
        functions: 70,
        statements: 70,
        branches: 60,
      },
    },
  },
})
