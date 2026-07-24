<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { SecretProfileSummary } from '../../shared/contracts'
import PageHeader from '../components/PageHeader.vue'
import PathField from '../components/PathField.vue'

const provider = ref('agnes')
const mediaType = ref<'image' | 'video'>('image')
const output = ref('')
const promptFile = ref('')
const interval = ref(90)
const concurrency = ref(1)
const maxErrors = ref(3)
const maxAttempts = ref(3)
const maxFailures = ref(20)
const maxRequests = ref(1000)
const maxWallHours = ref(24)
const retryBase = ref(15)
const retryMax = ref(300)
const maxErrorRate = ref(0.5)
const errorWindow = ref(20)
const minimumSamples = ref(6)
const pollInterval = ref(30)
const pollTimeout = ref(2400)
const downloadOutputs = ref(true)
const failOnAnyError = ref(false)
const model = ref('agnes-image-2.1-flash')
const numFrames = ref(241)
const frameRate = ref(24)
const width = ref<number | undefined>()
const height = ref<number | undefined>()
const negativePrompt = ref('')
const autoEnrollNamedCorpus = ref(false)
const collectionName = ref('')
const running = ref(false)
const profiles = ref<SecretProfileSummary[]>([])
const credentialProfileId = ref('')

const availableProfiles = computed(() => profiles.value.filter(profile =>
  profile.provider.toLowerCase() === provider.value && profile.unlocked,
))
const modelItems = computed(() => mediaType.value === 'image'
  ? ['agnes-image-2.1-flash']
  : ['agnes-video-v2.0'])

onMounted(async () => {
  profiles.value = await window.mel.secrets.list()
  credentialProfileId.value = availableProfiles.value[0]?.id ?? ''
})

async function run() {
  running.value = true
  try {
    await window.mel.jobs.create({
      kind: 'automation',
      title: `${provider.value} ${mediaType.value} automation`,
      config: {
        provider: provider.value,
        media_type: mediaType.value,
        model: model.value,
        output_path: output.value,
        prompt_file: promptFile.value,
        interval_seconds: interval.value,
        concurrency: concurrency.value,
        max_consecutive_errors: maxErrors.value,
        max_attempts_per_prompt: maxAttempts.value,
        max_failures: maxFailures.value,
        max_requests: maxRequests.value,
        max_wall_time_seconds: maxWallHours.value * 3600,
        retry_base_seconds: retryBase.value,
        retry_max_seconds: retryMax.value,
        max_error_rate: maxErrorRate.value,
        error_rate_window: errorWindow.value,
        error_rate_minimum_samples: minimumSamples.value,
        poll_interval_seconds: pollInterval.value,
        poll_timeout_seconds: pollTimeout.value,
        download_outputs: downloadOutputs.value,
        fail_job_on_any_error: failOnAnyError.value,
        num_frames: numFrames.value,
        frame_rate: frameRate.value,
        width: width.value,
        height: height.value,
        negative_prompt: negativePrompt.value || undefined,
        auto_enroll_named_corpus: autoEnrollNamedCorpus.value,
        collection_name: collectionName.value || undefined,
        credential_profile_id: credentialProfileId.value,
      },
    })
  } finally {
    running.value = false
  }
}
</script>

<template>
  <div class="page-wrap">
    <PageHeader eyebrow="Media Automation" title="Rate-conscious generation orchestration" subtitle="Durable submission, video polling, verified Generated Media, bounded retries and circuit breakers run outside the renderer." icon="mdi-robot-outline" color="accent" />
    <v-alert v-if="!availableProfiles.length" type="warning" variant="tonal" class="mb-5" title="No unlocked Agnes credential">
      Create or unlock a compatible credential profile in Settings. The API key is injected only into the isolated engine process.
    </v-alert>
    <v-card class="glass pa-6">
      <v-row>
        <v-col cols="12" md="4"><v-select v-model="provider" label="Provider" :items="['agnes']" prepend-inner-icon="mdi-cloud-outline" /></v-col>
        <v-col cols="12" md="4"><v-select v-model="credentialProfileId" label="Credential profile" :items="availableProfiles.map(profile => ({ title: `${profile.name} · ${profile.backend}`, value: profile.id }))" prepend-inner-icon="mdi-key-chain-variant" /></v-col>
        <v-col cols="12" md="4"><v-select v-model="mediaType" label="Media type" :items="['image', 'video']" prepend-inner-icon="mdi-movie-open-outline" @update:model-value="model = modelItems[0]" /></v-col>
        <v-col cols="12" md="4"><v-select v-model="model" label="Provider model" :items="modelItems" prepend-inner-icon="mdi-brain" /></v-col>
        <v-col cols="12" md="4"><v-text-field v-model.number="interval" type="number" min="0" label="Create interval (seconds)" prepend-inner-icon="mdi-timer-outline" /></v-col>
        <v-col cols="12" md="4"><v-text-field v-model.number="concurrency" type="number" min="1" max="8" label="Concurrent workers" prepend-inner-icon="mdi-call-split" /></v-col>
        <v-col cols="12">
          <PathField v-model="promptFile" kind="file" :extensions="['txt', 'jsonl']" label="Prompt text or JSONL file" hint="JSONL may include id, category and prompt fields." />
          <PathField v-model="output" label="Generated media output" hint="State, audit events, media, collection manifests and SHA receipts remain together." />
        </v-col>
      </v-row>

      <v-expand-transition>
        <v-card v-if="mediaType === 'video'" variant="tonal" color="secondary" class="pa-4 mb-5">
          <v-row>
            <v-col cols="12" md="3"><v-text-field v-model.number="numFrames" type="number" min="1" label="Frames" /></v-col>
            <v-col cols="12" md="3"><v-text-field v-model.number="frameRate" type="number" min="1" label="Frame rate" /></v-col>
            <v-col cols="12" md="3"><v-text-field v-model.number="width" type="number" min="64" label="Width (optional)" clearable /></v-col>
            <v-col cols="12" md="3"><v-text-field v-model.number="height" type="number" min="64" label="Height (optional)" clearable /></v-col>
            <v-col cols="12"><v-text-field v-model="negativePrompt" label="Negative prompt (optional)" /></v-col>
          </v-row>
        </v-card>
      </v-expand-transition>

      <v-card variant="tonal" color="primary" class="pa-4 mb-5">
        <div class="d-flex align-center ga-3 mb-2">
          <v-icon icon="mdi-folder-check-outline" />
          <div><div class="font-weight-bold">Generated Media collection</div><div class="text-caption">Every downloaded file is decoded again. Corrupt media is quarantined; verified media becomes content-addressed blobs.</div></div>
        </div>
        <v-row>
          <v-col cols="12" md="5"><v-switch v-model="autoEnrollNamedCorpus" color="primary" label="Auto-enroll verified successes into a named local corpus" hide-details /></v-col>
          <v-col cols="12" md="7"><v-text-field v-model="collectionName" label="Named corpus" prepend-inner-icon="mdi-folder-star-outline" :disabled="!autoEnrollNamedCorpus" /></v-col>
        </v-row>
      </v-card>

      <v-expansion-panels variant="accordion" class="mb-6">
        <v-expansion-panel title="Reliability, retry and budget controls">
          <v-expansion-panel-text>
            <v-row>
              <v-col cols="12" sm="6" lg="3"><v-text-field v-model.number="maxErrors" type="number" min="1" label="Consecutive error breaker" /></v-col>
              <v-col cols="12" sm="6" lg="3"><v-text-field v-model.number="maxAttempts" type="number" min="1" label="Attempts per prompt" /></v-col>
              <v-col cols="12" sm="6" lg="3"><v-text-field v-model.number="maxFailures" type="number" min="1" label="Failure budget" /></v-col>
              <v-col cols="12" sm="6" lg="3"><v-text-field v-model.number="maxRequests" type="number" min="1" label="Request budget" /></v-col>
              <v-col cols="12" sm="6" lg="3"><v-text-field v-model.number="maxWallHours" type="number" min="1" label="Wall-time budget (hours)" /></v-col>
              <v-col cols="12" sm="6" lg="3"><v-text-field v-model.number="retryBase" type="number" min="1" label="Retry base seconds" /></v-col>
              <v-col cols="12" sm="6" lg="3"><v-text-field v-model.number="retryMax" type="number" min="1" label="Retry maximum seconds" /></v-col>
              <v-col cols="12" sm="6" lg="3"><v-text-field v-model.number="maxErrorRate" type="number" min="0" max="1" step="0.05" label="Rolling max error rate" /></v-col>
              <v-col cols="12" sm="6" lg="3"><v-text-field v-model.number="errorWindow" type="number" min="1" label="Rolling window" /></v-col>
              <v-col cols="12" sm="6" lg="3"><v-text-field v-model.number="minimumSamples" type="number" min="1" label="Minimum breaker samples" /></v-col>
              <v-col cols="12" sm="6" lg="3"><v-text-field v-model.number="pollInterval" type="number" min="1" label="Video poll interval" /></v-col>
              <v-col cols="12" sm="6" lg="3"><v-text-field v-model.number="pollTimeout" type="number" min="1" label="Video poll timeout" /></v-col>
            </v-row>
            <v-switch v-model="downloadOutputs" color="primary" label="Download and hash verified outputs" />
            <v-switch v-model="failOnAnyError" color="warning" label="Mark the whole job failed when any prompt exhausts retries" />
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <v-btn color="primary" prepend-icon="mdi-play" :loading="running" :disabled="!output || !promptFile || !credentialProfileId || (autoEnrollNamedCorpus && !collectionName)" @click="run">
        Start durable automation
      </v-btn>
    </v-card>
  </div>
</template>
