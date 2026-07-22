<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { ModelRecord } from '../../shared/contracts'
import PageHeader from '../components/PageHeader.vue'

const builtInModels = ref<ModelRecord[]>([])
const customModels = ref<ModelRecord[]>([])
const models = computed(() => [...builtInModels.value, ...customModels.value])
const busy = ref<string>()
const message = ref('')
const snackbar = ref(false)
const installedCount = computed(() => models.value.filter(model => model.installed).length)

async function refresh() {
  ;[builtInModels.value, customModels.value] = await Promise.all([
    window.mel.models.list(),
    window.melCustomModels.list(),
  ])
}
function notify(text: string) { message.value = text; snackbar.value = true }
async function importModel(model: ModelRecord) {
  const path = await window.mel.chooseFile({ title: `Import ${model.family} ${model.variant}`, extensions: ['onnx'] })
  if (!path) return
  busy.value = model.id
  try {
    await window.mel.models.import(model.id, path)
    notify(`Imported ${model.family} ${model.variant}`)
    await refresh()
  } catch (error) {
    notify(error instanceof Error ? error.message : String(error))
  } finally {
    busy.value = undefined
  }
}
async function importManifest() {
  const path = await window.mel.chooseFile({ title: 'Import declarative detector manifest', extensions: ['json'] })
  if (!path) return
  busy.value = 'manifest'
  try {
    const model = await window.melCustomModels.import(path)
    notify(`Imported user-supplied ${model.family} ${model.variant}.`)
    await refresh()
  } catch (error) {
    notify(error instanceof Error ? error.message : String(error))
  } finally {
    busy.value = undefined
  }
}
async function remove(model: ModelRecord) {
  busy.value = model.id
  try {
    if (model.id.startsWith('user-')) await window.melCustomModels.remove(model.id)
    else await window.mel.models.remove(model.id)
    await refresh()
  } finally {
    busy.value = undefined
  }
}
async function reveal(model: ModelRecord) {
  if (model.localPath) await window.mel.revealPath(model.localPath)
}

onMounted(refresh)
</script>

<template>
  <div class="page-wrap">
    <PageHeader eyebrow="Model Manager" title="Verified model registry" subtitle="Every detector is identified by family, variant, adapter, labels, artifact hash and distribution state. User manifests may only select built-in decoders; executable plugins are rejected." icon="mdi-cube-outline" />
    <div class="d-flex flex-wrap align-center ga-3 mb-6">
      <v-alert variant="tonal" color="primary" icon="mdi-database-check-outline" class="flex-grow-1 mb-0">
        {{ installedCount }} / {{ models.length }} models installed. Import only artifacts obtained under rights you are allowed to use.
      </v-alert>
      <v-btn color="secondary" prepend-icon="mdi-file-code-outline" :loading="busy === 'manifest'" @click="importManifest">Import manifest + ONNX</v-btn>
    </div>
    <v-alert type="info" variant="tonal" class="mb-6">
      Declarative manifests support only `yolox-v1` and `nanodet-plus-v1`, adjacent `.onnx` files, COCO-80 labels, pinned SHA-256 and a license note. No Python, JavaScript, DLL, remote URL or arbitrary WASM is executed.
    </v-alert>
    <v-row>
      <v-col v-for="model in models" :key="model.id" cols="12" md="6" xl="4">
        <v-hover v-slot="{ isHovering, props }">
          <v-card v-bind="props" class="glass module-card pa-5 h-100" :class="{ 'is-hovered': isHovering }">
            <div class="d-flex justify-space-between">
              <v-avatar :color="model.family === 'YOLOX' ? 'primary' : 'secondary'" variant="tonal" rounded="lg"><v-icon icon="mdi-cube-scan" /></v-avatar>
              <div class="d-flex ga-2">
                <v-chip v-if="model.id.startsWith('user-')" color="info" variant="tonal">User supplied</v-chip>
                <v-chip :color="model.installed ? 'success' : 'warning'" variant="tonal">{{ model.installed ? 'Installed' : 'Not installed' }}</v-chip>
              </div>
            </div>
            <div class="text-overline mt-5">{{ model.family }}</div>
            <div class="text-h5 font-weight-bold">{{ model.variant }}</div>
            <div class="d-flex flex-wrap ga-2 mt-3">
              <v-chip size="small" variant="outlined">{{ model.inputWidth }}×{{ model.inputHeight }}</v-chip>
              <v-chip size="small" variant="outlined">{{ model.computeTier }}</v-chip>
              <v-chip size="small" color="warning" variant="tonal">{{ model.licenseState }}</v-chip>
            </div>
            <div class="text-caption text-medium-emphasis mt-4">Adapter: {{ model.adapter }} · Labels: {{ model.labels }}</div>
            <div v-if="model.sha256" class="text-caption mt-2 text-truncate">SHA-256 {{ model.sha256 }}</div>
            <div class="d-flex ga-2 mt-5">
              <v-btn v-if="!model.installed" color="primary" prepend-icon="mdi-import" :loading="busy === model.id" @click="importModel(model)">Import ONNX</v-btn>
              <template v-else>
                <v-btn color="secondary" variant="tonal" prepend-icon="mdi-folder-open-outline" @click="reveal(model)">Reveal</v-btn>
                <v-btn color="error" variant="text" prepend-icon="mdi-delete-outline" :loading="busy === model.id" @click="remove(model)">Remove</v-btn>
              </template>
            </div>
          </v-card>
        </v-hover>
      </v-col>
    </v-row>
    <v-snackbar v-model="snackbar" :timeout="5000">{{ message }}</v-snackbar>
  </div>
</template>
