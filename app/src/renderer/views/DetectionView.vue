<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { ModelRecord, SystemInfo } from '../../shared/contracts'
import type {
  DetectionBrowserResult,
  DetectionPreset,
  DetectionPresetSnapshot,
} from '../../shared/detection-workflow-contracts'
import type { HardwarePreferences, HardwareProviderKey } from '../../shared/hardware-contracts'
import PageHeader from '../components/PageHeader.vue'
import PathField from '../components/PathField.vue'

type ProviderSupport = Record<HardwareProviderKey, { provider: string; available: boolean }>
type ProviderAwareSystemInfo = SystemInfo & {
  engineProviders?: {
    runtime_version: string
    runtime_device: string
    available_providers: string[]
    provider_support: Partial<ProviderSupport>
    distributions: Record<string, string>
  }
}

const tab = ref<'run' | 'benchmark' | 'results' | 'presets'>('run')
const input = ref('')
const output = ref('')
const modelId = ref('')
const provider = ref<HardwareProviderKey>('cpu')
const deviceId = ref(0)
const coremlComputeUnits = ref<HardwarePreferences['coremlComputeUnits']>('ALL')
const allowProviderFallback = ref(true)
const threshold = ref(0.35)
const nmsThreshold = ref(0.45)
const maxDetections = ref(300)
const sampleEveryNFrames = ref(1)
const sampleTargetFps = ref(0)
const maxSampledFrames = ref(0)
const exportAnnotatedVideo = ref(true)
const exportCrops = ref(true)
const loading = ref(false)
const models = ref<ModelRecord[]>([])
const providerInventory = ref<ProviderAwareSystemInfo['engineProviders']>()

const benchmarkInput = ref('')
const benchmarkOutput = ref('')
const benchmarkModelIds = ref<string[]>([])
const benchmarkProviders = ref<HardwareProviderKey[]>(['cpu'])
const benchmarkSampleCount = ref(4)
const warmIterations = ref(10)
const benchmarkLoading = ref(false)

const resultManifestPath = ref('')
const resultQuery = ref('')
const resultClass = ref('')
const resultMinConfidence = ref(0)
const resultPage = ref(1)
const resultPageSize = ref(48)
const resultLoading = ref(false)
const browser = ref<DetectionBrowserResult>()

const presets = ref<DetectionPresetSnapshot>({ schemaVersion: 1, presets: [] })
const selectedPresetId = ref('')
const presetName = ref('')
const presetLoading = ref(false)

const installed = computed(() => models.value.filter(model => model.installed && model.localPath && model.sha256))
const selected = computed(() => installed.value.find(model => model.id === modelId.value))
const selectedBenchmarkModels = computed(() => installed.value.filter(model => benchmarkModelIds.value.includes(model.id)))
const providerLabels: Record<HardwareProviderKey, string> = {
  cpu: 'CPU', directml: 'DirectML', cuda: 'CUDA', coreml: 'CoreML',
}
const providerOptions = computed(() => (Object.keys(providerLabels) as HardwareProviderKey[]).map(value => {
  const support = providerInventory.value?.provider_support?.[value]
  const available = value === 'cpu' || support?.available === true
  return {
    title: `${providerLabels[value]}${available ? '' : ' · unavailable'}`,
    value,
    props: { disabled: !available },
  }
}))
const availableProviderKeys = computed(() => providerOptions.value
  .filter(item => !item.props.disabled)
  .map(item => item.value))
const selectedProviderAvailable = computed(() =>
  provider.value === 'cpu' || providerInventory.value?.provider_support?.[provider.value]?.available === true)
const providerPolicyText = computed(() => {
  if (provider.value === 'cpu') return 'CPU is the only configured execution provider.'
  return allowProviderFallback.value
    ? `The accelerator is first priority on device ${deviceId.value}; unsupported graph nodes may run on CPU.`
    : `Strict mode targets device ${deviceId.value}, disables implicit CPU execution and fails if the accelerator cannot run the graph.`
})
const resultPages = computed(() => Math.max(1, Math.ceil((browser.value?.totalItems ?? 0) / resultPageSize.value)))
const resultExports = computed(() => Object.entries(browser.value?.exports ?? {})
  .filter((entry): entry is [string, string] => typeof entry[1] === 'string'))

onMounted(async () => {
  const [builtIn, custom, systemInfo, hardwarePreferences, presetSnapshot] = await Promise.all([
    window.mel.models.list(),
    window.melCustomModels.list(),
    window.mel.systemInfo() as Promise<ProviderAwareSystemInfo>,
    window.melHardware.preferences.get(),
    window.melDetection.presets.list(),
  ])
  models.value = [...builtIn, ...custom]
  providerInventory.value = systemInfo.engineProviders
  modelId.value = installed.value[0]?.id ?? ''
  benchmarkModelIds.value = installed.value.slice(0, 2).map(model => model.id)
  provider.value = hardwarePreferences.provider
  deviceId.value = hardwarePreferences.deviceId
  allowProviderFallback.value = hardwarePreferences.allowCpuFallback
  coremlComputeUnits.value = hardwarePreferences.coremlComputeUnits
  if (!selectedProviderAvailable.value) provider.value = 'cpu'
  presets.value = presetSnapshot
  if (presetSnapshot.defaultPresetId) {
    selectedPresetId.value = presetSnapshot.defaultPresetId
    applyPreset(presetSnapshot.defaultPresetId)
  }
})

function normalizedBaseConfig(model: ModelRecord, providerKey: HardwareProviderKey) {
  return {
    input_path: input.value,
    output_path: output.value,
    model_id: model.id,
    model_path: model.localPath,
    model_sha256: model.sha256,
    adapter: model.adapter,
    input_width: model.inputWidth,
    input_height: model.inputHeight,
    labels: model.labels,
    execution_provider: providerKey,
    allow_provider_fallback: providerKey === 'cpu' ? false : allowProviderFallback.value,
    device_id: Math.max(0, Math.trunc(deviceId.value)),
    coreml_compute_units: coremlComputeUnits.value,
    score_threshold: threshold.value,
    nms_iou_threshold: nmsThreshold.value,
    max_detections: Math.max(1, Math.trunc(maxDetections.value)),
  }
}

async function run() {
  if (!selected.value?.localPath || !selectedProviderAvailable.value) return
  loading.value = true
  try {
    await window.mel.jobs.create({
      kind: 'detection',
      title: `Detect media with ${selected.value.family} ${selected.value.variant}`,
      config: {
        ...normalizedBaseConfig(selected.value, provider.value),
        sample_every_n_frames: Math.max(1, Math.trunc(sampleEveryNFrames.value)),
        sample_target_fps: Math.max(0, sampleTargetFps.value),
        max_sampled_frames: Math.max(0, Math.trunc(maxSampledFrames.value)),
        export_annotated_video: exportAnnotatedVideo.value,
        export_crops: exportCrops.value,
      },
    })
  } finally {
    loading.value = false
  }
}

async function runBenchmarkSuite() {
  if (!benchmarkInput.value || !benchmarkOutput.value || !selectedBenchmarkModels.value.length) return
  benchmarkLoading.value = true
  try {
    const suiteId = `benchmark-${new Date().toISOString().replace(/[:.]/gu, '-')}`
    const root = benchmarkOutput.value.replace(/[\\/]+$/u, '')
    for (const model of selectedBenchmarkModels.value) {
      for (const providerKey of benchmarkProviders.value.filter(item => availableProviderKeys.value.includes(item))) {
        const providerFolder = providerKey === 'cpu' ? 'cpu' : `${providerKey}-${Math.max(0, Math.trunc(deviceId.value))}`
        await window.mel.jobs.create({
          kind: 'detection',
          title: `Benchmark ${model.family} ${model.variant} · ${providerLabels[providerKey]}`,
          config: {
            ...normalizedBaseConfig(model, providerKey),
            input_path: benchmarkInput.value,
            output_path: `${root}/${suiteId}/${model.id}/${providerFolder}`,
            benchmark_mode: true,
            benchmark_suite_id: suiteId,
            benchmark_sample_count: Math.max(1, Math.trunc(benchmarkSampleCount.value)),
            warm_iterations: Math.max(1, Math.trunc(warmIterations.value)),
          },
        })
      }
    }
  } finally {
    benchmarkLoading.value = false
  }
}

async function chooseResultManifest() {
  const path = await window.mel.chooseFile({ title: 'Open detection manifest', extensions: ['json'] })
  if (path) {
    resultManifestPath.value = path
    resultPage.value = 1
    await loadResults()
  }
}

async function loadResults() {
  if (!resultManifestPath.value) return
  resultLoading.value = true
  try {
    browser.value = await window.melDetection.browse({
      manifestPath: resultManifestPath.value,
      query: resultQuery.value,
      className: resultClass.value,
      minConfidence: resultMinConfidence.value,
      page: resultPage.value,
      pageSize: resultPageSize.value,
    })
  } finally {
    resultLoading.value = false
  }
}

async function changeResultPage(page: number) {
  resultPage.value = page
  await loadResults()
}

function currentPresetPayload() {
  return {
    id: selectedPresetId.value || undefined,
    name: presetName.value.trim() || 'Detection preset',
    modelId: modelId.value,
    provider: provider.value,
    benchmarkModelIds: benchmarkModelIds.value,
    benchmarkProviders: benchmarkProviders.value,
    deviceId: Math.max(0, Math.trunc(deviceId.value)),
    coremlComputeUnits: coremlComputeUnits.value,
    allowCpuFallback: allowProviderFallback.value,
    scoreThreshold: threshold.value,
    nmsIouThreshold: nmsThreshold.value,
    maxDetections: Math.max(1, Math.trunc(maxDetections.value)),
    sampleEveryNFrames: Math.max(1, Math.trunc(sampleEveryNFrames.value)),
    sampleTargetFps: Math.max(0, sampleTargetFps.value),
    maxSampledFrames: Math.max(0, Math.trunc(maxSampledFrames.value)),
    exportAnnotatedVideo: exportAnnotatedVideo.value,
    exportCrops: exportCrops.value,
    benchmarkSampleCount: Math.max(1, Math.trunc(benchmarkSampleCount.value)),
    warmIterations: Math.max(1, Math.trunc(warmIterations.value)),
  }
}

async function savePreset() {
  presetLoading.value = true
  try {
    presets.value = await window.melDetection.presets.save(currentPresetPayload())
    const match = presets.value.presets.find(item => item.name === (presetName.value.trim() || 'Detection preset'))
    if (match) selectedPresetId.value = match.id
  } finally {
    presetLoading.value = false
  }
}

function applyPreset(id: string) {
  const preset = presets.value.presets.find(item => item.id === id)
  if (!preset) return
  selectedPresetId.value = preset.id
  presetName.value = preset.name
  modelId.value = preset.modelId || installed.value[0]?.id || ''
  provider.value = availableProviderKeys.value.includes(preset.provider) ? preset.provider : 'cpu'
  benchmarkModelIds.value = preset.benchmarkModelIds.filter(item => installed.value.some(model => model.id === item))
  benchmarkProviders.value = preset.benchmarkProviders.filter(item => availableProviderKeys.value.includes(item))
  if (!benchmarkProviders.value.length) benchmarkProviders.value = ['cpu']
  deviceId.value = preset.deviceId
  coremlComputeUnits.value = preset.coremlComputeUnits
  allowProviderFallback.value = preset.allowCpuFallback
  threshold.value = preset.scoreThreshold
  nmsThreshold.value = preset.nmsIouThreshold
  maxDetections.value = preset.maxDetections
  sampleEveryNFrames.value = preset.sampleEveryNFrames
  sampleTargetFps.value = preset.sampleTargetFps
  maxSampledFrames.value = preset.maxSampledFrames
  exportAnnotatedVideo.value = preset.exportAnnotatedVideo
  exportCrops.value = preset.exportCrops
  benchmarkSampleCount.value = preset.benchmarkSampleCount
  warmIterations.value = preset.warmIterations
}

async function removePreset() {
  if (!selectedPresetId.value) return
  presets.value = await window.melDetection.presets.remove(selectedPresetId.value)
  selectedPresetId.value = ''
  presetName.value = ''
}

async function setDefaultPreset() {
  presets.value = await window.melDetection.presets.setDefault(selectedPresetId.value || undefined)
}

function formatSeconds(value?: number) {
  if (value === undefined) return ''
  return `${value.toFixed(3)} s`
}
</script>

<template>
  <div class="page-wrap">
    <PageHeader eyebrow="Detection Studio" title="Resumable image and video inference" subtitle="Run verified models, export annotated media and structured datasets, compare cold and steady-state performance, and search result evidence without re-running inference." icon="mdi-vector-square" color="accent" />
    <v-alert v-if="!installed.length" type="warning" variant="tonal" class="mb-5" title="Install a model first">Open Model Manager and import a verified ONNX artifact or declarative user model manifest.</v-alert>

    <v-tabs v-model="tab" color="accent" class="mb-4">
      <v-tab value="run" prepend-icon="mdi-play-circle-outline">Run</v-tab>
      <v-tab value="benchmark" prepend-icon="mdi-speedometer">Benchmark</v-tab>
      <v-tab value="results" prepend-icon="mdi-image-search-outline">Results & crops</v-tab>
      <v-tab value="presets" prepend-icon="mdi-tune-variant">Presets</v-tab>
    </v-tabs>

    <v-window v-model="tab">
      <v-window-item value="run">
        <v-card class="glass pa-6">
          <PathField v-model="input" label="Image or video corpus" />
          <PathField v-model="output" label="Detection output directory" />
          <v-row>
            <v-col cols="12" md="3"><v-select v-model="modelId" label="Installed model" :items="installed.map(model => ({ title: `${model.family} ${model.variant}${model.id.startsWith('user-') ? ' · user' : ''}`, value: model.id }))" prepend-inner-icon="mdi-cube-outline" /></v-col>
            <v-col cols="12" md="3"><v-select v-model="provider" label="Execution provider" :items="providerOptions" prepend-inner-icon="mdi-expansion-card-variant" /></v-col>
            <v-col cols="12" md="2"><v-text-field v-model.number="deviceId" type="number" label="Device ID" :min="0" :max="64" prepend-inner-icon="mdi-identifier" /></v-col>
            <v-col cols="12" md="2"><v-slider v-model="threshold" label="Score" min="0.05" max="0.95" step="0.05" thumb-label color="accent" /></v-col>
            <v-col cols="12" md="2"><v-slider v-model="nmsThreshold" label="NMS IoU" min="0.1" max="0.9" step="0.05" thumb-label color="secondary" /></v-col>
            <v-col v-if="provider === 'coreml'" cols="12" md="4"><v-select v-model="coremlComputeUnits" label="CoreML compute units" :items="['ALL', 'CPU_ONLY', 'CPU_AND_GPU', 'CPU_AND_NE']" prepend-inner-icon="mdi-apple" /></v-col>
            <v-col cols="12" md="4"><v-text-field v-model.number="maxDetections" type="number" label="Maximum boxes per item" :min="1" :max="100000" prepend-inner-icon="mdi-format-list-numbered" /></v-col>
            <v-col cols="12" md="4" class="d-flex align-center"><v-switch v-model="allowProviderFallback" label="CPU fallback" color="secondary" inset hide-details :disabled="provider === 'cpu'" /></v-col>
          </v-row>

          <v-divider class="my-5" />
          <div class="text-subtitle-1 font-weight-bold mb-3">Video sampling and output</div>
          <v-row>
            <v-col cols="12" md="4"><v-text-field v-model.number="sampleEveryNFrames" type="number" label="Sample every N frames" :min="1" :max="1000000" prepend-inner-icon="mdi-movie-filter-outline" hint="Frame-index sampling is deterministic and resumable." persistent-hint /></v-col>
            <v-col cols="12" md="4"><v-text-field v-model.number="sampleTargetFps" type="number" label="Maximum sampled FPS" :min="0" :max="240" step="0.1" prepend-inner-icon="mdi-timer-outline" hint="0 disables the FPS cap; both sampling rules may apply." persistent-hint /></v-col>
            <v-col cols="12" md="4"><v-text-field v-model.number="maxSampledFrames" type="number" label="Maximum sampled frames" :min="0" :max="10000000" prepend-inner-icon="mdi-stop-circle-outline" hint="0 processes the full video." persistent-hint /></v-col>
            <v-col cols="12" md="4"><v-switch v-model="exportAnnotatedVideo" label="Export annotated MP4" color="accent" inset /></v-col>
            <v-col cols="12" md="4"><v-switch v-model="exportCrops" label="Export per-class crops" color="secondary" inset /></v-col>
          </v-row>

          <v-alert v-if="providerInventory" color="secondary" variant="tonal" density="compact" class="mb-4">ONNX Runtime {{ providerInventory.runtime_version }} · {{ providerInventory.runtime_device }} · {{ providerInventory.available_providers.join(', ') }}</v-alert>
          <v-alert v-else color="warning" variant="tonal" density="compact" class="mb-4">Provider inventory is unavailable. Detection remains limited to the verified CPU path.</v-alert>
          <v-alert color="info" variant="tonal" density="compact" class="mb-4">{{ providerPolicyText }}</v-alert>
          <v-alert v-if="selected" color="info" variant="tonal" density="compact" class="mb-4">{{ selected.adapter }} · {{ selected.inputWidth }}×{{ selected.inputHeight }} · {{ selected.sha256?.slice(0, 16) }}… <span v-if="selected.id.startsWith('user-')"> · user-supplied-only</span></v-alert>
          <v-btn color="accent" prepend-icon="mdi-crosshairs-gps" :loading="loading" :disabled="!input || !output || !selected || !selectedProviderAvailable" @click="run">Start detection</v-btn>
        </v-card>
      </v-window-item>

      <v-window-item value="benchmark">
        <v-card class="glass pa-6">
          <v-alert color="info" variant="tonal" class="mb-5" title="One durable job per model and provider">The suite records fresh-session cold latency separately from steady-state median and p95. Existing resource budgets and device queues remain authoritative.</v-alert>
          <PathField v-model="benchmarkInput" label="Benchmark image or video corpus" />
          <PathField v-model="benchmarkOutput" label="Benchmark output root" />
          <v-row>
            <v-col cols="12" md="6"><v-select v-model="benchmarkModelIds" multiple chips closable-chips label="Models" :items="installed.map(model => ({ title: `${model.family} ${model.variant}`, value: model.id }))" prepend-inner-icon="mdi-cube-scan" /></v-col>
            <v-col cols="12" md="6"><v-select v-model="benchmarkProviders" multiple chips closable-chips label="Providers" :items="providerOptions" prepend-inner-icon="mdi-expansion-card-variant" /></v-col>
            <v-col cols="12" md="3"><v-text-field v-model.number="benchmarkSampleCount" type="number" label="Input samples" :min="1" :max="64" prepend-inner-icon="mdi-image-multiple-outline" /></v-col>
            <v-col cols="12" md="3"><v-text-field v-model.number="warmIterations" type="number" label="Steady iterations" :min="1" :max="200" prepend-inner-icon="mdi-repeat" /></v-col>
            <v-col cols="12" md="3"><v-text-field v-model.number="deviceId" type="number" label="Device ID" :min="0" :max="64" prepend-inner-icon="mdi-identifier" /></v-col>
            <v-col cols="12" md="3" class="d-flex align-center"><v-switch v-model="allowProviderFallback" label="CPU fallback" color="secondary" inset /></v-col>
          </v-row>
          <v-btn color="accent" prepend-icon="mdi-speedometer" :loading="benchmarkLoading" :disabled="!benchmarkInput || !benchmarkOutput || !selectedBenchmarkModels.length || !benchmarkProviders.length" @click="runBenchmarkSuite">Queue benchmark matrix</v-btn>
        </v-card>
      </v-window-item>

      <v-window-item value="results">
        <v-card class="glass pa-6 mb-5">
          <div class="d-flex flex-wrap ga-3 align-center mb-4">
            <v-text-field v-model="resultManifestPath" label="detection-manifest.json" prepend-inner-icon="mdi-file-document-outline" hide-details class="flex-grow-1" />
            <v-btn color="secondary" variant="tonal" prepend-icon="mdi-file-search-outline" @click="chooseResultManifest">Choose</v-btn>
            <v-btn color="accent" prepend-icon="mdi-refresh" :loading="resultLoading" :disabled="!resultManifestPath" @click="loadResults">Load</v-btn>
          </div>
          <v-row>
            <v-col cols="12" md="5"><v-text-field v-model="resultQuery" label="Search path, item or class" prepend-inner-icon="mdi-magnify" @keyup.enter="loadResults" /></v-col>
            <v-col cols="12" md="4"><v-select v-model="resultClass" label="Class filter" clearable :items="browser?.classNames ?? []" prepend-inner-icon="mdi-tag-search-outline" /></v-col>
            <v-col cols="12" md="3"><v-slider v-model="resultMinConfidence" label="Minimum confidence" min="0" max="1" step="0.05" thumb-label color="secondary" /></v-col>
          </v-row>
          <v-btn color="secondary" variant="tonal" prepend-icon="mdi-filter-check-outline" :disabled="!resultManifestPath" @click="() => { resultPage = 1; loadResults() }">Apply filters</v-btn>
        </v-card>

        <template v-if="browser">
          <v-row class="mb-2">
            <v-col cols="12" md="4"><v-card class="glass pa-4"><div class="text-caption">Filtered items</div><div class="text-h5">{{ browser.totalItems }}</div></v-card></v-col>
            <v-col cols="12" md="4"><v-card class="glass pa-4"><div class="text-caption">Manifest sampled items</div><div class="text-h5">{{ browser.sampledItemCount }}</div></v-card></v-col>
            <v-col cols="12" md="4"><v-card class="glass pa-4"><div class="text-caption">Total boxes</div><div class="text-h5">{{ browser.boxCount }}</div></v-card></v-col>
          </v-row>

          <v-card v-if="resultExports.length" class="glass pa-5 mb-5">
            <div class="text-subtitle-1 font-weight-bold mb-3">Structured exports</div>
            <div v-for="[name, path] in resultExports" :key="name" class="d-flex flex-wrap ga-3 align-center mb-2">
              <v-chip color="secondary" variant="tonal">{{ name }}</v-chip>
              <code class="text-caption flex-grow-1 text-truncate">{{ path }}</code>
              <v-btn size="small" variant="text" prepend-icon="mdi-folder-open-outline" @click="window.mel.revealPath(path)">Reveal</v-btn>
            </div>
          </v-card>

          <v-row>
            <v-col v-for="item in browser.items" :key="item.itemId" cols="12" lg="6">
              <v-card class="glass pa-5 h-100">
                <div class="d-flex justify-space-between ga-3 mb-2">
                  <div>
                    <div class="text-subtitle-1 font-weight-bold">{{ item.sourceType === 'video-frame' ? `Frame ${item.frameIndex}` : item.itemId }}</div>
                    <div v-if="item.timestampSeconds !== undefined" class="text-caption">{{ formatSeconds(item.timestampSeconds) }}</div>
                  </div>
                  <v-chip :color="item.detectionCount ? 'accent' : 'secondary'" variant="tonal">{{ item.detectionCount }} boxes</v-chip>
                </div>
                <div class="text-caption text-truncate mb-3" :title="item.sourcePath">{{ item.sourcePath }}</div>
                <div class="d-flex flex-wrap ga-2 mb-3">
                  <v-chip v-for="name in item.classes" :key="name" size="small" color="secondary" variant="outlined">{{ name }}</v-chip>
                  <v-chip v-if="!item.classes.length" size="small" variant="outlined">No detections</v-chip>
                </div>
                <v-table density="compact" class="mb-3">
                  <thead><tr><th>Class</th><th>Confidence</th><th>Area</th><th>Crop</th></tr></thead>
                  <tbody>
                    <tr v-for="(detection, index) in item.detections" :key="`${item.itemId}-${index}`">
                      <td>{{ detection.className }}</td>
                      <td>{{ detection.confidence.toFixed(3) }}</td>
                      <td>{{ (detection.areaFraction * 100).toFixed(2) }}%</td>
                      <td><v-btn v-if="detection.cropPath" size="x-small" variant="text" icon="mdi-crop" :aria-label="`Reveal ${detection.className} crop`" @click="window.mel.revealPath(detection.cropPath)" /></td>
                    </tr>
                  </tbody>
                </v-table>
                <v-btn v-if="item.annotatedPath" size="small" color="accent" variant="tonal" prepend-icon="mdi-image-outline" @click="window.mel.revealPath(item.annotatedPath)">Reveal annotated media</v-btn>
              </v-card>
            </v-col>
          </v-row>
          <v-pagination v-if="resultPages > 1" :model-value="resultPage" :length="resultPages" class="mt-4" @update:model-value="changeResultPage" />
        </template>
      </v-window-item>

      <v-window-item value="presets">
        <v-card class="glass pa-6">
          <v-alert color="info" variant="tonal" class="mb-5">Presets store inference, sampling, export and benchmark defaults locally. They never contain media, model bytes or credentials.</v-alert>
          <v-row>
            <v-col cols="12" md="5"><v-select v-model="selectedPresetId" label="Saved preset" clearable :items="presets.presets.map(item => ({ title: `${item.name}${item.id === presets.defaultPresetId ? ' · default' : ''}`, value: item.id }))" prepend-inner-icon="mdi-tune-variant" @update:model-value="value => value && applyPreset(value)" /></v-col>
            <v-col cols="12" md="5"><v-text-field v-model="presetName" label="Preset name" prepend-inner-icon="mdi-form-textbox" /></v-col>
            <v-col cols="12" md="2" class="d-flex align-center"><v-chip v-if="selectedPresetId === presets.defaultPresetId" color="accent" variant="tonal">Default</v-chip></v-col>
          </v-row>
          <div class="d-flex flex-wrap ga-3">
            <v-btn color="accent" prepend-icon="mdi-content-save-outline" :loading="presetLoading" @click="savePreset">Save current settings</v-btn>
            <v-btn color="secondary" variant="tonal" prepend-icon="mdi-star-outline" :disabled="!selectedPresetId" @click="setDefaultPreset">Set default</v-btn>
            <v-btn color="error" variant="tonal" prepend-icon="mdi-delete-outline" :disabled="!selectedPresetId" @click="removePreset">Remove</v-btn>
          </div>
        </v-card>
      </v-window-item>
    </v-window>
  </div>
</template>
