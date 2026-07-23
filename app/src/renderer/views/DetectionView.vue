<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { ModelRecord } from '../../shared/contracts'
import PageHeader from '../components/PageHeader.vue'
import PathField from '../components/PathField.vue'

const input = ref('')
const output = ref('')
const modelId = ref('')
const provider = ref('cpu')
const threshold = ref(0.35)
const nmsThreshold = ref(0.45)
const loading = ref(false)
const models = ref<ModelRecord[]>([])

const installed = computed(() => models.value.filter(model => model.installed))
const selected = computed(() => installed.value.find(model => model.id === modelId.value))

onMounted(async () => {
  const [builtIn, custom] = await Promise.all([
    window.mel.models.list(),
    window.melCustomModels.list(),
  ])
  models.value = [...builtIn, ...custom]
  modelId.value = installed.value[0]?.id ?? ''
})

async function run() {
  if (!selected.value?.localPath) return
  loading.value = true
  try {
    await window.mel.jobs.create({
      kind: 'detection',
      title: `Detect with ${selected.value.family} ${selected.value.variant}`,
      config: {
        input_path: input.value,
        output_path: output.value,
        model_id: selected.value.id,
        model_path: selected.value.localPath,
        model_sha256: selected.value.sha256,
        adapter: selected.value.adapter,
        input_width: selected.value.inputWidth,
        input_height: selected.value.inputHeight,
        labels: selected.value.labels,
        execution_provider: provider.value,
        score_threshold: threshold.value,
        nms_iou_threshold: nmsThreshold.value,
        max_detections: 300,
      },
    })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-wrap">
    <PageHeader
      eyebrow="Detection Studio"
      title="Multi-model inference with durable checkpoints"
      subtitle="Run built-in registry slots or hash-pinned user-supplied ONNX manifests through the same verified YOLOX and NanoDet decoders."
      icon="mdi-vector-square"
      color="accent"
    />
    <v-alert v-if="!installed.length" type="warning" variant="tonal" class="mb-5" title="Install a model first">
      Open Model Manager and import a verified ONNX artifact or declarative user model manifest.
    </v-alert>
    <v-card class="glass pa-6">
      <PathField v-model="input" label="Image corpus" />
      <PathField v-model="output" label="Detection output directory" />
      <v-row>
        <v-col cols="12" md="4">
          <v-select
            v-model="modelId"
            label="Installed model"
            :items="installed.map(model => ({ title: `${model.family} ${model.variant}${model.id.startsWith('user-') ? ' · user' : ''}`, value: model.id }))"
            prepend-inner-icon="mdi-cube-outline"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-select
            v-model="provider"
            label="Execution provider"
            :items="['cpu', 'directml', 'cuda', 'coreml']"
            prepend-inner-icon="mdi-expansion-card-variant"
          />
        </v-col>
        <v-col cols="12" md="2">
          <v-slider v-model="threshold" label="Score" min="0.05" max="0.95" step="0.05" thumb-label color="accent" />
        </v-col>
        <v-col cols="12" md="2">
          <v-slider v-model="nmsThreshold" label="NMS IoU" min="0.1" max="0.9" step="0.05" thumb-label color="secondary" />
        </v-col>
      </v-row>
      <v-alert v-if="selected" color="info" variant="tonal" density="compact" class="mb-4">
        {{ selected.adapter }} · {{ selected.inputWidth }}×{{ selected.inputHeight }} · {{ selected.sha256?.slice(0, 16) }}…
        <span v-if="selected.id.startsWith('user-')"> · user-supplied-only</span>
      </v-alert>
      <v-btn color="accent" prepend-icon="mdi-crosshairs-gps" :loading="loading" :disabled="!input || !output || !selected" @click="run">
        Start detection
      </v-btn>
    </v-card>
  </div>
</template>
