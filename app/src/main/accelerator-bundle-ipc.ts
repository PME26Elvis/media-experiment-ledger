import { ipcMain } from 'electron'
import { z } from 'zod'
import { ACCELERATOR_BUNDLE_IPC } from '../shared/accelerator-bundle-contracts'
import type { AcceleratorBundleManager } from './accelerator-bundle-manager'

const identity = z.object({
  bundleId: z.string().regex(/^[a-z0-9][a-z0-9._-]{2,79}$/u),
  version: z.string().regex(/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/u),
})
const pathSchema = z.string().min(1).max(32768)

export function registerAcceleratorBundleIpc(manager: AcceleratorBundleManager): void {
  ipcMain.handle(ACCELERATOR_BUNDLE_IPC.snapshot, () => manager.snapshot())
  ipcMain.handle(ACCELERATOR_BUNDLE_IPC.install, (_event, manifestPath: string) => manager.install(pathSchema.parse(manifestPath)))
  ipcMain.handle(ACCELERATOR_BUNDLE_IPC.activate, (_event, bundleId: string, version: string) => {
    const parsed = identity.parse({ bundleId, version })
    return manager.activate(parsed.bundleId, parsed.version)
  })
  ipcMain.handle(ACCELERATOR_BUNDLE_IPC.rollback, () => manager.rollback())
  ipcMain.handle(ACCELERATOR_BUNDLE_IPC.quarantine, (_event, bundleId: string, version: string, reason: string) => {
    const parsed = identity.extend({ reason: z.string().min(1).max(1000) }).parse({ bundleId, version, reason })
    return manager.quarantine(parsed.bundleId, parsed.version, parsed.reason)
  })
  ipcMain.handle(ACCELERATOR_BUNDLE_IPC.remove, (_event, bundleId: string, version: string) => {
    const parsed = identity.parse({ bundleId, version })
    return manager.remove(parsed.bundleId, parsed.version)
  })
}
