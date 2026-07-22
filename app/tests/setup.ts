import { vi } from 'vitest'
Object.defineProperty(window, 'mel', { value: { systemInfo: vi.fn(), chooseDirectory: vi.fn(), chooseFile: vi.fn(), revealPath: vi.fn(), settings: { get: vi.fn(), set: vi.fn() }, jobs: { list: vi.fn(), create: vi.fn(), control: vi.fn() }, models: { list: vi.fn(), import: vi.fn(), remove: vi.fn() }, updater: { check: vi.fn(), install: vi.fn() } }, writable: true })
