<script setup lang="ts">
import { onMounted, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import PathField from '../components/PathField.vue'

const imagePath = ref('')
const videoPath = ref('')
const projectPath = ref('')
const mode = ref('adaptive')
const workers = ref(4)
const submitted = ref(false)

onMounted(async () => {
  const settings = await window.mel.settings.get()
  imagePath.value = settings.imageInputPath
  videoPath.value = settings.videoInputPath
  projectPath.value = settings.generatedOutputPath
})

async function run() {
  await window.mel.jobs.create({
    kind: 'scan',
    title: 'Index imported media',
    config: {
      image_path: imagePath.value,
      video_path: videoPath.value,
      output_path: projectPath.value,
      import_mode: mode.value,
      workers: workers.value,
    },
  })
  submitted.value = true
}
</script>

<template>
  <div class="page-wrap">
    <PageHeader eyebrow="Media Import" title="Bring large corpora under control" subtitle="Choose independent sources, storage policy and a project directory. The engine hashes, deduplicates, generates display-pixel-aware proxies and can materialize portable content-addressed copies." icon="mdi-folder-multiple-image" color="secondary" />
    <v-card class="glass pa-6">
      <v-row>
        <v-col cols="12" md="6"><PathField v-model="imagePath" label="Image input directory" hint="Existing references remain untouched." /></v-col>
        <v-col cols="12" md="6"><PathField v-model="videoPath" label="Video input directory" hint="Video indexing generates verified poster proxies." /></v-col>
        <v-col cols="12"><PathField v-model="projectPath" label="Project materialization directory" hint="Stores media-index.json, proxy pyramids and optional managed blobs." /></v-col>
        <v-col cols="12" md="8">
          <v-select v-model="mode" label="Storage policy" :items="[
            { title: 'Adaptive recommendation', value: 'adaptive' },
            { title: 'Managed content-addressed copy', value: 'copy' },
            { title: 'External reference', value: 'reference' },
          ]" prepend-inner-icon="mdi-database-arrow-right-outline" />
        </v-col>
        <v-col cols="12" md="4"><v-text-field v-model.number="workers" type="number" min="1" max="8" label="Bounded workers" prepend-inner-icon="mdi-account-hard-hat-outline" /></v-col>
      </v-row>
      <v-alert variant="tonal" type="info" class="mb-5">
        Adaptive mode chooses a managed copy only when the corpus is below the configured threshold and enough free disk remains. Otherwise it preserves external references.
      </v-alert>
      <v-btn color="primary" prepend-icon="mdi-database-search-outline" :disabled="(!imagePath && !videoPath) || !projectPath" @click="run">Index corpus</v-btn>
      <v-alert v-if="submitted" type="success" variant="tonal" class="mt-5">Import job created. Progress and recovery controls are available in Job Center.</v-alert>
    </v-card>
  </div>
</template>
