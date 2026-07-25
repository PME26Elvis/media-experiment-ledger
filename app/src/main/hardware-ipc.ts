import { ipcMain } from 'electron'
import { z } from 'zod'
import { HARDWARE_IPC, type HardwarePreferences, type HardwareSelfTestRequest, type HardwareSelfTestResult } from '../shared/hardware-contracts'
import { HardwareRuntimeManager } from './hardware-runtime-manager'

const providerSchema = z.enum(['cpu', 'directml', 'cuda', 'coreml'])
const computeUnitsSchema = z.enum(['ALL', 'CPU_ONLY', 'CPU_AND_GPU', 'CPU_AND_NE'])
const preferencePatchSchema = z.object({
  provider: providerSchema.optional(),
  deviceId: z.number().int().min(0).max(64).optional(),
  allowCpuFallback: z.boolean().optional(),
  coremlComputeUnits: computeUnitsSchema.optional(),
})
const selfTestSchema = z.object({
  provider: providerSchema,
  deviceId: z.number().int().min(0).max(64),
  allowCpuFallback: z.boolean(),
  coremlComputeUnits: computeUnitsSchema,
  warmRuns: z.number().int().min(1).max(20).optional(),
})

export function registerHardwareIpc(userDataPath: string): void {
  const manager = new HardwareRuntimeManager(userDataPath)
  ipcMain.handle(HARDWARE_IPC.snapshot, (_event, refresh?: boolean) => manager.snapshot(Boolean(refresh)))
  ipcMain.handle(HARDWARE_IPC.selfTest, (_event, request: HardwareSelfTestRequest) => manager.selfTest(selfTestSchema.parse(request)))
  ipcMain.handle(HARDWARE_IPC.preferencesGet, () => manager.preferences())
  ipcMain.handle(HARDWARE_IPC.preferencesSet, (_event, patch: Partial<HardwarePreferences>) => manager.savePreferences(preferencePatchSchema.parse(patch)))
  ipcMain.handle(HARDWARE_IPC.clearCache, (_event, provider: string) => manager.clearCache(providerSchema.parse(provider)))
  ipcMain.handle(HARDWARE_IPC.exportEvidence, (_event, outputDirectory: string, selfTest?: HardwareSelfTestResult) =>
    manager.exportEvidence(z.string().min(1).max(32768).parse(outputDirectory), selfTest))
}
