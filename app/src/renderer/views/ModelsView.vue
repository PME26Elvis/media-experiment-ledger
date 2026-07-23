<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { ModelRecord } from '../../shared/contracts'
import PageHeader from '../components/PageHeader.vue'

const builtInModels = ref<ModelRecord[]>([])
const customModels = ref<ModelRecord[]>([])
const busy = ref<string>()
const message = ref('')
const snackbar = ref(false)

const models = computed(() => [...builtInModels.value, ...customModels.value])
const installedCount = computed(() => models.value.filter(model => model.installed).length)

function isCustom(model: ModelRecord): boolean {
  return model.id.startsWith('user-')
}

async function refresh() {
  const [builtIn, custom] = await Promise.all([
    window.mel.models.list(),
    window.melCustomModels.list(),
  ])
  builtInModels.value = builtIn
  customModels.value = custom
}

function notify(text: string) {
  message.value = text
  snackbar.value = true
}

async function importBuiltInModel(model: ModelRecord) {
  const path = await window.mel.chooseFile({
    title: `Import ${model.family} ${model.variant}`,
    extensions: ['onnx'],
  })
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

async function importCustomManifest() {
  const path = await window.mel.chooseFile({
    title: 'Import declarative model manifest',
    extensions: ['json'],
  })
  if (!path) return
  busy.value = 'custom-import'
  try {
    const record = await window.melCustomModels.import(path)
    notify(`Imported user-supplied ${record.family} ${record.variant}`)
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
    if (isCustom(model)) await window.melCustomModels.remove(model.id)
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
    <PageHeader
      eyebrow="Model Manager"
      title="Verified model registry"
      subtitle="Built-in model slots and declarative user-supplied manifests share the same hash, adapter and provenance boundary. No manifest may execute code."
      icon="mdi-cube-outline"
    >
      <v-btn
        color="secondary"
        variant="tonal"
        prepend-icon="mdi-file-code-outline"
        :loading="busy === 'custom-import'"
        @click="importCustomManifest"
      >
        Import model manifest
      </v-btn>
    </PageHeader>

    <v-alert variant="tonal" color="primary" icon="mdi-database-check-outline" class="mb-6">
      {{ installedCount }} / {{ models.length }} models installed. User manifests must reference an adjacent hash-pinned ONNX file and one of the built-in decoders.
    </v-alert>

    <v-row>
      <v-col v-for="model in models" :key="model.id" cols="12" md="6" xl="4">
        <v-hover v-slot="hover">
          <v-card v-bind="hover?.props" class="glass module-card pa-5 h-100" :class="{ 'is-hovered': Boolean(hover?.isHovering) }">
            <div class="d-flex justify-space-between ga-2">
              <v-avatar :color="model.family === 'YOLOX' ? 'primary' : 'secondary'" variant="tonal" rounded="lg">
                <v-icon icon="mdi-cube-scan" />
              </v-avatar>
              <div class="d-flex flex-wrap justify-end ga-1">
                <v-chip v-if="isCustom(model)" color="accent" variant="tonal" size="small">User supplied</v-chip>
                <v-chip :color="model.installed ? 'success' : 'warning'" variant="tonal" size="small">
                  {{ model.installed ? 'Installed' : 'Not installed' }}
                </v-chip>
              </div>
            </div>
            <div class="text-overline mt-5">{{ model.family }}</div>
            <div class="text-h5 font-weight-bold">{{ model.variant }}</div>
            <div class="d-flex flex-wrap ga-2 mt-3">
              <v-chip size="small" variant="outlined">{{ model.inputWidth }}×{{ model.inputHeight }}</v-chip>
              <v-chip size="small" variant="outlined">{{ model.computeTier }}</v-chip>
              <v-chip size="small" color="warning" variant="tonal">{{ model.licenseState }}</v-chip>
            </div>
            <div class="text-caption text-medium-emphasis mt-4">
              Adapter: {{ model.adapter }} · Labels: {{ model.labels }}
            </div>
            <div v-if="model.sha256" class="text-caption mt-2 text-truncate">SHA-256 {{ model.sha256 }}</div>
            <div class="d-flex flex-wrap ga-2 mt-5">
              <v-btn
                v-if="!model.installed && !isCustom(model)"
                color="primary"
                prepend-icon="mdi-import"
                :loading="busy === model.id"
                @click="importBuiltInModel(model)"
              >
                Import ONNX
              </v-btn>
              <template v-else-if="model.installed">
                <v-btn color="secondary" variant="tonal" prepend-icon="mdi-folder-open-outline" @click="reveal(model)">
                  Reveal
                </v-btn>
                <v-btn color="error" variant="text" prepend-icon="mdi-delete-outline" :loading="busy === model.id" @click="remove(model)">
                  Remove
                </v-btn>
              </template>
            </div>
          </v-card>
        </v-hover>
      </v-col>
    </v-row>
    <v-snackbar v-model="snackbar" :timeout="5000">{{ message }}</v-snackbar>
  </div>
</template>
