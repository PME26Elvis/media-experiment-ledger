import { randomUUID } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, renameSync, unlinkSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import type {
  DetectionBrowserDetection,
  DetectionBrowserItem,
  DetectionBrowserRequest,
  DetectionBrowserResult,
  DetectionPreset,
  DetectionPresetSnapshot,
} from '../shared/detection-workflow-contracts'
import type { HardwareProviderKey } from '../shared/hardware-contracts'

type JsonRecord = Record<string, unknown>

const PROVIDERS = new Set<HardwareProviderKey>(['cpu', 'directml', 'cuda', 'coreml'])
const COREML_UNITS = new Set<DetectionPreset['coremlComputeUnits']>(['ALL', 'CPU_ONLY', 'CPU_AND_GPU', 'CPU_AND_NE'])

function finiteNumber(value: unknown, fallback: number, minimum: number, maximum: number): number {
  const candidate = typeof value === 'number' && Number.isFinite(value) ? value : fallback
  return Math.max(minimum, Math.min(maximum, candidate))
}

function finiteInteger(value: unknown, fallback: number, minimum: number, maximum: number): number {
  return Math.trunc(finiteNumber(value, fallback, minimum, maximum))
}

function stringValue(value: unknown, fallback = '', maximum = 32768): string {
  return typeof value === 'string' ? value.slice(0, maximum) : fallback
}

function stringArray(value: unknown, maximum = 32): string[] {
  return Array.isArray(value)
    ? [...new Set(value.filter(item => typeof item === 'string').map(item => item.slice(0, 160)))].slice(0, maximum)
    : []
}

function provider(value: unknown, fallback: HardwareProviderKey = 'cpu'): HardwareProviderKey {
  return typeof value === 'string' && PROVIDERS.has(value as HardwareProviderKey)
    ? value as HardwareProviderKey
    : fallback
}

function providers(value: unknown): HardwareProviderKey[] {
  const normalized = Array.isArray(value)
    ? value.map(item => provider(item, 'cpu')).filter((item, index, list) => list.indexOf(item) === index)
    : []
  return normalized.length ? normalized : ['cpu']
}

function normalizePreset(value: unknown, existing?: DetectionPreset): DetectionPreset {
  const record = value && typeof value === 'object' ? value as JsonRecord : {}
  const now = new Date().toISOString()
  const id = stringValue(record.id, existing?.id ?? randomUUID(), 160)
  const computeUnits = stringValue(record.coremlComputeUnits, existing?.coremlComputeUnits ?? 'ALL', 40)
  const benchmarkModelIds = stringArray(record.benchmarkModelIds)
  return {
    id,
    name: stringValue(record.name, existing?.name ?? 'Detection preset', 120).trim() || 'Detection preset',
    modelId: stringValue(record.modelId, existing?.modelId ?? '', 160),
    provider: provider(record.provider, existing?.provider ?? 'cpu'),
    benchmarkModelIds: benchmarkModelIds.length ? benchmarkModelIds : existing?.benchmarkModelIds ?? [],
    benchmarkProviders: Array.isArray(record.benchmarkProviders)
      ? providers(record.benchmarkProviders)
      : existing?.benchmarkProviders ?? ['cpu'],
    deviceId: finiteInteger(record.deviceId, existing?.deviceId ?? 0, 0, 64),
    coremlComputeUnits: COREML_UNITS.has(computeUnits as DetectionPreset['coremlComputeUnits'])
      ? computeUnits as DetectionPreset['coremlComputeUnits']
      : 'ALL',
    allowCpuFallback: typeof record.allowCpuFallback === 'boolean' ? record.allowCpuFallback : existing?.allowCpuFallback ?? true,
    scoreThreshold: finiteNumber(record.scoreThreshold, existing?.scoreThreshold ?? 0.35, 0.01, 0.99),
    nmsIouThreshold: finiteNumber(record.nmsIouThreshold, existing?.nmsIouThreshold ?? 0.45, 0.01, 0.99),
    maxDetections: finiteInteger(record.maxDetections, existing?.maxDetections ?? 300, 1, 100_000),
    sampleEveryNFrames: finiteInteger(record.sampleEveryNFrames, existing?.sampleEveryNFrames ?? 1, 1, 1_000_000),
    sampleTargetFps: finiteNumber(record.sampleTargetFps, existing?.sampleTargetFps ?? 0, 0, 240),
    maxSampledFrames: finiteInteger(record.maxSampledFrames, existing?.maxSampledFrames ?? 0, 0, 10_000_000),
    exportAnnotatedVideo: typeof record.exportAnnotatedVideo === 'boolean'
      ? record.exportAnnotatedVideo
      : existing?.exportAnnotatedVideo ?? true,
    exportCrops: typeof record.exportCrops === 'boolean' ? record.exportCrops : existing?.exportCrops ?? true,
    benchmarkSampleCount: finiteInteger(record.benchmarkSampleCount, existing?.benchmarkSampleCount ?? 4, 1, 64),
    warmIterations: finiteInteger(record.warmIterations, existing?.warmIterations ?? 10, 1, 200),
    createdAt: existing?.createdAt ?? now,
    updatedAt: now,
  }
}

function readJson(path: string): unknown {
  return JSON.parse(readFileSync(path, 'utf8'))
}

function atomicWrite(path: string, value: unknown): void {
  mkdirSync(dirname(path), { recursive: true })
  const temporary = `${path}.tmp`
  writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, 'utf8')
  renameSync(temporary, path)
}

function normalizeDetection(value: unknown): DetectionBrowserDetection | undefined {
  const record = value && typeof value === 'object' ? value as JsonRecord : {}
  const className = stringValue(record.class_name, '', 200)
  if (!className) return undefined
  const bbox = Array.isArray(record.bbox_xyxy)
    ? record.bbox_xyxy.map(item => finiteNumber(item, 0, -1_000_000, 1_000_000)).slice(0, 4)
    : []
  return {
    classId: finiteInteger(record.class_id, 0, 0, 1_000_000),
    className,
    confidence: finiteNumber(record.confidence, 0, 0, 1),
    bboxXyxy: bbox,
    areaPixels: finiteNumber(record.area_pixels, 0, 0, Number.MAX_SAFE_INTEGER),
    areaFraction: finiteNumber(record.area_fraction, 0, 0, 1),
    cropPath: stringValue(record.crop_path) || undefined,
  }
}

function normalizeItem(value: unknown): DetectionBrowserItem | undefined {
  const record = value && typeof value === 'object' ? value as JsonRecord : {}
  const itemId = stringValue(record.item_id, '', 200)
  const sourcePath = stringValue(record.source_path)
  if (!itemId || !sourcePath) return undefined
  const detections = Array.isArray(record.detections)
    ? record.detections.map(normalizeDetection).filter((item): item is DetectionBrowserDetection => Boolean(item))
    : []
  const sourceType = record.source_type === 'video-frame' ? 'video-frame' : 'image'
  const annotated = record.annotated && typeof record.annotated === 'object'
    ? record.annotated as JsonRecord
    : {}
  return {
    itemId,
    sourcePath,
    sourceType,
    sourceWidth: finiteInteger(record.source_width, 0, 0, 1_000_000),
    sourceHeight: finiteInteger(record.source_height, 0, 0, 1_000_000),
    frameIndex: typeof record.frame_index === 'number' ? finiteInteger(record.frame_index, 0, 0, Number.MAX_SAFE_INTEGER) : undefined,
    timestampSeconds: typeof record.timestamp_seconds === 'number'
      ? finiteNumber(record.timestamp_seconds, 0, 0, Number.MAX_SAFE_INTEGER)
      : undefined,
    detectionCount: detections.length,
    classes: [...new Set(detections.map(item => item.className))].sort(),
    annotatedPath: stringValue(annotated.path) || undefined,
    detections,
  }
}

export class DetectionWorkflowManager {
  private readonly preferencesPath: string

  constructor(userDataPath: string) {
    this.preferencesPath = join(userDataPath, 'detection-workflow.json')
  }

  browse(request: DetectionBrowserRequest): DetectionBrowserResult {
    const manifestPath = resolve(stringValue(request.manifestPath))
    if (!existsSync(manifestPath)) throw new Error(`Detection manifest does not exist: ${manifestPath}`)
    const raw = readJson(manifestPath)
    if (!raw || typeof raw !== 'object') throw new Error('Detection manifest must be a JSON object.')
    const manifest = raw as JsonRecord
    const allItems = Array.isArray(manifest.items)
      ? manifest.items.map(normalizeItem).filter((item): item is DetectionBrowserItem => Boolean(item))
      : []
    const query = stringValue(request.query, '', 500).trim().toLowerCase()
    const className = stringValue(request.className, '', 200)
    const minConfidence = finiteNumber(request.minConfidence, 0, 0, 1)
    const filtered = allItems.filter(item => {
      const classMatch = !className || item.classes.includes(className)
      const confidenceMatch = minConfidence <= 0 || item.detections.some(detection => detection.confidence >= minConfidence)
      const queryMatch = !query || [item.itemId, item.sourcePath, item.sourceType, ...item.classes]
        .some(value => value.toLowerCase().includes(query))
      return classMatch && confidenceMatch && queryMatch
    })
    const pageSize = finiteInteger(request.pageSize, 48, 1, 200)
    const page = finiteInteger(request.page, 1, 1, Math.max(1, Math.ceil(filtered.length / pageSize)))
    const offset = (page - 1) * pageSize
    const explicitClassNames = stringArray(manifest.class_names, 1000)
    const classNames = explicitClassNames.length
      ? explicitClassNames
      : [...new Set(allItems.flatMap(item => item.classes))].sort()
    return {
      schemaVersion: 1,
      manifestPath,
      modelId: stringValue(manifest.model_id, '', 200) || undefined,
      requestedProvider: stringValue(manifest.requested_provider, '', 80) || undefined,
      sampledItemCount: finiteInteger(manifest.sampled_item_count, allItems.length, 0, Number.MAX_SAFE_INTEGER),
      boxCount: finiteInteger(manifest.box_count, allItems.reduce((sum, item) => sum + item.detectionCount, 0), 0, Number.MAX_SAFE_INTEGER),
      classNames,
      exports: manifest.exports && typeof manifest.exports === 'object' ? manifest.exports as JsonRecord : {},
      page,
      pageSize,
      totalItems: filtered.length,
      items: filtered.slice(offset, offset + pageSize),
    }
  }

  listPresets(): DetectionPresetSnapshot {
    if (!existsSync(this.preferencesPath)) return { schemaVersion: 1, presets: [] }
    try {
      const raw = readJson(this.preferencesPath)
      const record = raw && typeof raw === 'object' ? raw as JsonRecord : {}
      const presets = Array.isArray(record.presets)
        ? record.presets.map(item => normalizePreset(item)).sort((left, right) => left.name.localeCompare(right.name))
        : []
      const defaultPresetId = stringValue(record.defaultPresetId, '', 160)
      return {
        schemaVersion: 1,
        defaultPresetId: presets.some(item => item.id === defaultPresetId) ? defaultPresetId : undefined,
        presets,
      }
    } catch {
      return { schemaVersion: 1, presets: [] }
    }
  }

  savePreset(value: unknown): DetectionPresetSnapshot {
    const snapshot = this.listPresets()
    const record = value && typeof value === 'object' ? value as JsonRecord : {}
    const requestedId = stringValue(record.id, '', 160)
    const existing = snapshot.presets.find(item => item.id === requestedId)
    const preset = normalizePreset(record, existing)
    const presets = [...snapshot.presets.filter(item => item.id !== preset.id), preset]
      .sort((left, right) => left.name.localeCompare(right.name))
    const next = { schemaVersion: 1 as const, defaultPresetId: snapshot.defaultPresetId, presets }
    atomicWrite(this.preferencesPath, next)
    return next
  }

  removePreset(id: string): DetectionPresetSnapshot {
    const snapshot = this.listPresets()
    const presets = snapshot.presets.filter(item => item.id !== id)
    const next = {
      schemaVersion: 1 as const,
      defaultPresetId: snapshot.defaultPresetId === id ? undefined : snapshot.defaultPresetId,
      presets,
    }
    atomicWrite(this.preferencesPath, next)
    return next
  }

  setDefaultPreset(id?: string): DetectionPresetSnapshot {
    const snapshot = this.listPresets()
    const defaultPresetId = id && snapshot.presets.some(item => item.id === id) ? id : undefined
    const next = { ...snapshot, defaultPresetId }
    atomicWrite(this.preferencesPath, next)
    return next
  }

  reset(): void {
    try {
      unlinkSync(this.preferencesPath)
    } catch {
      // Already absent.
    }
  }
}
