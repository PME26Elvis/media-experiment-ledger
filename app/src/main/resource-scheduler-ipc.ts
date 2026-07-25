import { ipcMain } from 'electron'
import { z } from 'zod'
import { RESOURCE_SCHEDULER_IPC, type ResourceSchedulerPreferences } from '../shared/resource-scheduler-contracts'
import type { JobManager } from './job-manager'

const policySchema = z.object({
  maxConcurrent: z.number().int().min(1).max(32),
  memoryBudgetMb: z.number().int().min(256).max(262_144),
  safetyReserveMb: z.number().int().min(0).max(262_016),
}).refine(value => value.safetyReserveMb <= value.memoryBudgetMb - 128, {
  message: 'Safety reserve must leave at least 128 MB available.',
})

const preferencesPatchSchema = z.object({
  cpuMaxConcurrent: z.number().int().min(1).max(64).optional(),
  warmSessionIdleSeconds: z.number().int().min(0).max(3600).optional(),
  defaultAcceleratorPolicy: policySchema.optional(),
  devicePolicies: z.record(z.string().regex(/^(?:directml|cuda|coreml):\d+$/u), policySchema).optional(),
})

export function registerResourceSchedulerIpc(jobs: JobManager): void {
  ipcMain.handle(RESOURCE_SCHEDULER_IPC.snapshot, () => jobs.resourceSnapshot())
  ipcMain.handle(RESOURCE_SCHEDULER_IPC.preferencesGet, () => jobs.resourcePreferences())
  ipcMain.handle(RESOURCE_SCHEDULER_IPC.preferencesSet, (_event, patch: Partial<ResourceSchedulerPreferences>) =>
    jobs.updateResourcePreferences(preferencesPatchSchema.parse(patch)))
}
