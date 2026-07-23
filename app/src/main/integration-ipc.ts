import { ipcMain } from 'electron'
import { z } from 'zod'
import {
  INTEGRATION_IPC,
  type CloudSyncRequest,
  type GitHubPublishRequest,
  type SaveScheduleRequest,
  type WasmPostprocessRequest,
} from '../shared/integration-contracts'
import { CloudSyncManager } from './cloud-sync-manager'
import { GitHubReleasePublisher } from './github-release-publisher'
import { SchedulerManager } from './scheduler-manager'
import { runWasmPostprocessor } from './wasm-postprocessor'

const pathSchema = z.string().min(1).max(32768)
const idSchema = z.string().uuid()
const jobSchema = z.object({
  kind: z.enum(['scan', 'atlas', 'detection', 'automation', 'pdf-export', 'sample-download']),
  title: z.string().min(1).max(160),
  config: z.record(z.string(), z.unknown()),
})
const cadenceSchema = z.discriminatedUnion('kind', [
  z.object({ kind: z.literal('daily'), hour: z.number().int().min(0).max(23), minute: z.number().int().min(0).max(59) }),
  z.object({ kind: z.literal('weekly'), weekdays: z.array(z.number().int().min(0).max(6)).min(1).max(7), hour: z.number().int().min(0).max(23), minute: z.number().int().min(0).max(59) }),
  z.object({ kind: z.literal('interval'), hours: z.number().int().min(1).max(168) }),
])
const scheduleSchema = z.object({
  id: idSchema.optional(),
  name: z.string().min(1).max(120),
  enabled: z.boolean(),
  cadence: cadenceSchema,
  job: jobSchema,
})
const syncSchema = z.object({
  projectRoot: pathSchema,
  syncRoot: pathSchema,
  dryRun: z.boolean().optional(),
})
const publishSchema = z.object({
  repository: z.string().min(3).max(200),
  tag: z.string().min(1).max(200),
  name: z.string().min(1).max(200),
  body: z.string().max(125000),
  draft: z.boolean(),
  prerelease: z.boolean(),
  assetPaths: z.array(pathSchema).min(1).max(50),
  credentialProfileId: idSchema,
})
const wasmSchema = z.object({
  modulePath: pathSchema,
  sha256: z.string().regex(/^[a-fA-F0-9]{64}$/u),
  input: z.unknown(),
  timeoutMs: z.number().int().min(50).max(5000).optional(),
  maxMemoryPages: z.number().int().min(1).max(256).optional(),
})

export function registerIntegrationIpc(
  schedules: SchedulerManager,
  sync: CloudSyncManager,
  github: GitHubReleasePublisher,
): void {
  ipcMain.handle(INTEGRATION_IPC.schedulesList, () => schedules.list())
  ipcMain.handle(INTEGRATION_IPC.schedulesSave, (_event, request: SaveScheduleRequest) =>
    schedules.save(scheduleSchema.parse(request)))
  ipcMain.handle(INTEGRATION_IPC.schedulesRemove, (_event, id: string) => schedules.remove(idSchema.parse(id)))
  ipcMain.handle(INTEGRATION_IPC.schedulesRunNow, (_event, id: string) => schedules.runNow(idSchema.parse(id)))
  ipcMain.handle(INTEGRATION_IPC.schedulesPreview, (_event, request: SaveScheduleRequest) =>
    schedules.preview(scheduleSchema.parse(request)))
  ipcMain.handle(INTEGRATION_IPC.syncRun, (_event, request: CloudSyncRequest) =>
    sync.sync(syncSchema.parse(request)))
  ipcMain.handle(INTEGRATION_IPC.githubPublish, (_event, request: GitHubPublishRequest) =>
    github.publish(publishSchema.parse(request)))
  ipcMain.handle(INTEGRATION_IPC.wasmPostprocess, (_event, request: WasmPostprocessRequest) =>
    runWasmPostprocessor(wasmSchema.parse(request)))
}
