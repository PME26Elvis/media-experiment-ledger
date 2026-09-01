import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { afterEach, describe, expect, it } from 'vitest'
import { DetectionWorkflowManager } from '../src/main/detection-workflow-manager'

const roots: string[] = []

function temporaryRoot(): string {
  const root = mkdtempSync(join(tmpdir(), 'mel-detection-workflow-'))
  roots.push(root)
  return root
}

afterEach(() => {
  while (roots.length) rmSync(roots.pop()!, { recursive: true, force: true })
})

function preset(name: string) {
  return {
    name,
    modelId: 'yolox-tiny',
    provider: 'cpu',
    benchmarkModelIds: ['yolox-tiny', 'nanodet-plus'],
    benchmarkProviders: ['cpu'],
    deviceId: 0,
    coremlComputeUnits: 'ALL',
    allowCpuFallback: true,
    scoreThreshold: 0.35,
    nmsIouThreshold: 0.45,
    maxDetections: 300,
    sampleEveryNFrames: 3,
    sampleTargetFps: 5,
    maxSampledFrames: 100,
    exportAnnotatedVideo: true,
    exportCrops: true,
    benchmarkSampleCount: 4,
    warmIterations: 10,
  }
}

describe('DetectionWorkflowManager presets', () => {
  it('persists, updates, defaults and removes presets atomically', () => {
    const root = temporaryRoot()
    const manager = new DetectionWorkflowManager(root)
    const created = manager.savePreset(preset('Research video'))
    expect(created.presets).toHaveLength(1)
    const id = created.presets[0].id
    expect(created.presets[0].sampleEveryNFrames).toBe(3)

    const updated = manager.savePreset({ ...preset('Research video updated'), id, warmIterations: 20 })
    expect(updated.presets).toHaveLength(1)
    expect(updated.presets[0].name).toBe('Research video updated')
    expect(updated.presets[0].warmIterations).toBe(20)

    const defaulted = manager.setDefaultPreset(id)
    expect(defaulted.defaultPresetId).toBe(id)
    expect(new DetectionWorkflowManager(root).listPresets().defaultPresetId).toBe(id)

    const removed = manager.removePreset(id)
    expect(removed.presets).toEqual([])
    expect(removed.defaultPresetId).toBeUndefined()
  })
})

describe('DetectionWorkflowManager browser', () => {
  it('filters schema 7 results by text, class and confidence with pagination', () => {
    const root = temporaryRoot()
    const manifestPath = join(root, 'detection-manifest.json')
    writeFileSync(manifestPath, JSON.stringify({
      schema_version: 7,
      model_id: 'yolox-tiny',
      requested_provider: 'cpu',
      sampled_item_count: 3,
      box_count: 3,
      class_names: ['car', 'person'],
      exports: { csv: join(root, 'exports', 'detections.csv') },
      items: [
        {
          item_id: 'image-person', source_path: join(root, 'person.jpg'), source_type: 'image',
          source_width: 640, source_height: 480, annotated: { path: join(root, 'person-annotated.jpg') },
          detections: [{ class_id: 0, class_name: 'person', confidence: 0.92, bbox_xyxy: [1, 2, 3, 4], area_pixels: 4, area_fraction: 0.1, crop_path: join(root, 'person-crop.jpg') }],
        },
        {
          item_id: 'video-car', source_path: join(root, 'traffic.mp4'), source_type: 'video-frame',
          source_width: 1920, source_height: 1080, frame_index: 60, timestamp_seconds: 2,
          annotated: { path: join(root, 'frame.jpg') },
          detections: [{ class_id: 2, class_name: 'car', confidence: 0.81, bbox_xyxy: [10, 20, 30, 40], area_pixels: 400, area_fraction: 0.02 }],
        },
        {
          item_id: 'image-low-car', source_path: join(root, 'parking.jpg'), source_type: 'image',
          source_width: 320, source_height: 240, annotated: { path: join(root, 'parking-annotated.jpg') },
          detections: [{ class_id: 2, class_name: 'car', confidence: 0.3, bbox_xyxy: [5, 5, 10, 10], area_pixels: 25, area_fraction: 0.001 }],
        },
      ],
    }), 'utf8')

    const manager = new DetectionWorkflowManager(root)
    const first = manager.browse({
      manifestPath,
      query: 'traffic',
      className: 'car',
      minConfidence: 0.8,
      page: 1,
      pageSize: 1,
    })
    expect(first.totalItems).toBe(1)
    expect(first.items[0]).toMatchObject({
      itemId: 'video-car',
      sourceType: 'video-frame',
      frameIndex: 60,
      timestampSeconds: 2,
      detectionCount: 1,
    })
    expect(first.items[0].detections[0].className).toBe('car')
    expect(first.classNames).toEqual(['car', 'person'])
    expect(first.exports.csv).toContain('detections.csv')

    const paged = manager.browse({ manifestPath, className: 'car', page: 2, pageSize: 1 })
    expect(paged.totalItems).toBe(2)
    expect(paged.page).toBe(2)
    expect(paged.items).toHaveLength(1)
  })
})
