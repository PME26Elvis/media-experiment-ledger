import { ipcMain } from 'electron'
import { z } from 'zod'
import { DETECTION_WORKFLOW_IPC, type DetectionBrowserRequest } from '../shared/detection-workflow-contracts'
import { DetectionWorkflowManager } from './detection-workflow-manager'

const pathSchema = z.string().min(1).max(32768)
const idSchema = z.string().min(1).max(160)
const browseSchema = z.object({
  manifestPath: pathSchema,
  query: z.string().max(500).optional(),
  className: z.string().max(200).optional(),
  minConfidence: z.number().min(0).max(1).optional(),
  page: z.number().int().min(1).max(1_000_000).optional(),
  pageSize: z.number().int().min(1).max(200).optional(),
})
const presetSchema = z.object({
  id: z.string().max(160).optional(),
  name: z.string().min(1).max(120),
  modelId: z.string().max(160),
  provider: z.enum(['cpu', 'directml', 'cuda', 'coreml']),
  benchmarkModelIds: z.array(z.string().max(160)).max(32),
  benchmarkProviders: z.array(z.enum(['cpu', 'directml', 'cuda', 'coreml'])).min(1).max(4),
  deviceId: z.number().int().min(0).max(64),
  coremlComputeUnits: z.enum(['ALL', 'CPU_ONLY', 'CPU_AND_GPU', 'CPU_AND_NE']),
  allowCpuFallback: z.boolean(),
  scoreThreshold: z.number().min(0.01).max(0.99),
  nmsIouThreshold: z.number().min(0.01).max(0.99),
  maxDetections: z.number().int().min(1).max(100_000),
  sampleEveryNFrames: z.number().int().min(1).max(1_000_000),
  sampleTargetFps: z.number().min(0).max(240),
  maxSampledFrames: z.number().int().min(0).max(10_000_000),
  exportAnnotatedVideo: z.boolean(),
  exportCrops: z.boolean(),
  benchmarkSampleCount: z.number().int().min(1).max(64),
  warmIterations: z.number().int().min(1).max(200),
})

export function registerDetectionWorkflowIpc(manager: DetectionWorkflowManager): void {
  ipcMain.handle(DETECTION_WORKFLOW_IPC.browse, (_event, request: DetectionBrowserRequest) =>
    manager.browse(browseSchema.parse(request)))
  ipcMain.handle(DETECTION_WORKFLOW_IPC.presetsList, () => manager.listPresets())
  ipcMain.handle(DETECTION_WORKFLOW_IPC.presetsSave, (_event, preset: unknown) => manager.savePreset(presetSchema.parse(preset)))
  ipcMain.handle(DETECTION_WORKFLOW_IPC.presetsRemove, (_event, id: string) => manager.removePreset(idSchema.parse(id)))
  ipcMain.handle(DETECTION_WORKFLOW_IPC.presetsSetDefault, (_event, id?: string) =>
    manager.setDefaultPreset(id ? idSchema.parse(id) : undefined))
}
