import { basename } from 'node:path'
import { z } from 'zod'
import type { SampleCorpusManifest } from './contracts'

const allowedHosts = new Set([
  'github.com',
  'objects.githubusercontent.com',
  'release-assets.githubusercontent.com',
  'raw.githubusercontent.com',
])

const assetSchema = z.object({
  id: z.string().min(1),
  mediaType: z.enum(['image', 'video', 'metadata', 'mixed']),
  part: z.number().int().positive(),
  fileName: z.string().min(1).refine((value) => basename(value) === value),
  url: z.string().url().refine((value) => new URL(value).protocol === 'https:'),
  sha256: z.string().regex(/^[a-f0-9]{64}$/u),
  sizeBytes: z.number().int().nonnegative(),
  required: z.boolean(),
})

const manifestSchema = z.object({
  schemaVersion: z.literal(1),
  id: z.string().regex(/^[a-z0-9][a-z0-9._-]+$/u),
  tier: z.enum(['quick-start', 'full-research']),
  version: z.number().int().positive(),
  title: z.string().min(1),
  description: z.string(),
  releaseTag: z.string().min(1),
  generatedAt: z.string().datetime(),
  rightsStatus: z.enum(['approved', 'review-required', 'blocked']),
  license: z.string().min(1),
  sourceReleaseTags: z.array(z.string()),
  sanitization: z.object({
    prompts: z.enum(['sanitized-full', 'ids-only']),
    removedFields: z.array(z.string()),
  }),
  assets: z.array(assetSchema),
})

export function validateSampleCorpusManifest(value: unknown): SampleCorpusManifest {
  const manifest = manifestSchema.parse(value) as SampleCorpusManifest
  const ids = new Set<string>()
  for (const asset of manifest.assets) {
    const host = new URL(asset.url).hostname
    if (!allowedHosts.has(host)) {
      throw new Error(`Corpus asset host is not allowlisted: ${host}`)
    }
    if (ids.has(asset.id)) {
      throw new Error(`Duplicate corpus asset id: ${asset.id}`)
    }
    ids.add(asset.id)
  }
  return manifest
}
