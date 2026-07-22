<script setup lang="ts">
import { ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import PathField from '../components/PathField.vue'

const input = ref('')
const output = ref('')
const template = ref('Traditional Chinese Academic')
const mode = ref('full')
const videoPdfMode = ref('three-frame-strip')
const createGifPreview = ref(true)
const loading = ref(false)
const templates = [
  'Research Light',
  'Editorial Dark',
  'Gallery Minimal',
  'Technical Audit',
  'Executive Review',
  'Traditional Chinese Academic',
  '16:9 Presentation Report',
]

async function run() {
  loading.value = true
  try {
    await window.mel.jobs.create({
      kind: 'atlas',
      title: 'Build Prompt Repeatability Atlas',
      config: {
        input_path: input.value,
        output_path: output.value,
        template: template.value,
        scope: mode.value,
        video_pdf_mode: videoPdfMode.value,
        create_gif_preview: createGifPreview.value,
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
      eyebrow="Atlas Studio"
      title="Evidence first. Presentation second."
      subtitle="Create resumable immutable image/video evidence, then author a structured or controlled-freeform PDF without changing source media."
      icon="mdi-image-multiple-outline"
      color="secondary"
    />
    <v-row>
      <v-col cols="12" lg="7">
        <v-card class="glass pa-6">
          <PathField v-model="input" label="Atlas input corpus" />
          <PathField v-model="output" label="Atlas output directory" />
          <v-row>
            <v-col cols="12" md="7">
              <v-select v-model="template" label="Report template" :items="templates" prepend-inner-icon="mdi-palette-outline" />
            </v-col>
            <v-col cols="12" md="5">
              <v-select
                v-model="mode"
                label="Evidence scope"
                :items="[{ title: 'Full corpus', value: 'full' }, { title: 'Selected collection', value: 'selected' }]"
                prepend-inner-icon="mdi-filter-variant"
              />
            </v-col>
            <v-col cols="12" md="7">
              <v-select
                v-model="videoPdfMode"
                label="Static video evidence"
                :items="[
                  { title: '10% · 50% · 90% strip', value: 'three-frame-strip' },
                  { title: 'Poster frame', value: 'poster' },
                ]"
                prepend-inner-icon="mdi-filmstrip-box-multiple"
              />
            </v-col>
            <v-col cols="12" md="5">
              <v-switch v-model="createGifPreview" color="secondary" label="Create lightweight GIF previews" hide-details />
            </v-col>
          </v-row>
          <v-btn
            color="secondary"
            prepend-icon="mdi-image-sync-outline"
            :loading="loading"
            :disabled="!input || !output"
            @click="run"
          >
            Build resumable Atlas snapshot
          </v-btn>
        </v-card>
      </v-col>
      <v-col cols="12" lg="5">
        <v-card class="glass pa-6 h-100">
          <div class="text-overline text-secondary">Video evidence policy</div>
          <div class="text-h5 font-weight-bold mt-2">10% · 50% · 90%</div>
          <p class="text-body-2 text-medium-emphasis mt-3">
            GIF and video sources are decoded locally. The immutable snapshot stores source SHA, selected frame indexes and timestamps, strip/poster hashes, optional GIF preview, and any decode warning.
          </p>
          <v-list bg-color="transparent" density="compact" class="mt-4">
            <v-list-item prepend-icon="mdi-check-decagram-outline" title="Image and video cohorts remain separate" />
            <v-list-item prepend-icon="mdi-restart" title="Per-page and per-video checkpoint recovery" />
            <v-list-item prepend-icon="mdi-file-certificate-outline" title="All derived evidence receives SHA-256" />
          </v-list>
          <v-icon icon="mdi-file-pdf-box" color="error" size="72" class="mt-5" />
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>
