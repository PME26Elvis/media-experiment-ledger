import { z } from 'zod'
import type { UserModelManifest } from './custom-model-contracts'

const fileName = z.string().min(1).max(255).refine(value => !value.includes('/') && !value.includes('\\') && value.toLowerCase().endsWith('.onnx'), 'modelFile must be an adjacent ONNX filename')

export const userModelManifestSchema = z.object({
  schemaVersion: z.literal(1),
  displayName: z.string().min(1).max(120),
  family: z.enum(['YOLOX', 'NanoDet-Plus']),
  variant: z.string().min(1).max(100).regex(/^[A-Za-z0-9._+ -]+$/u),
  adapter: z.enum(['yolox-v1', 'nanodet-plus-v1']),
  inputWidth: z.number().int().min(160).max(4096),
  inputHeight: z.number().int().min(160).max(4096),
  labels: z.literal('coco-80'),
  modelFile: fileName,
  modelSha256: z.string().regex(/^[0-9a-f]{64}$/iu),
  licenseNote: z.string().min(1).max(2000),
}).superRefine((value, context) => {
  if (value.family === 'YOLOX' && value.adapter !== 'yolox-v1') {
    context.addIssue({ code: 'custom', path: ['adapter'], message: 'YOLOX requires yolox-v1.' })
  }
  if (value.family === 'NanoDet-Plus' && value.adapter !== 'nanodet-plus-v1') {
    context.addIssue({ code: 'custom', path: ['adapter'], message: 'NanoDet-Plus requires nanodet-plus-v1.' })
  }
})

export function parseUserModelManifest(value: unknown): UserModelManifest {
  return userModelManifestSchema.parse(value) as UserModelManifest
}
