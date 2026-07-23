<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { DiagnosticsPayload, TelemetryConsent } from '../../shared/diagnostics-contracts'
import PageHeader from '../components/PageHeader.vue'
import PathField from '../components/PathField.vue'

const preview = ref<DiagnosticsPayload>()
const consent = ref<TelemetryConsent>()
const outputDirectory = ref('')
const busy = ref('')
const message = ref('')
const messageType = ref<'success' | 'info' | 'warning' | 'error'>('info')
const snackbar = ref(false)
const previewJson = computed(() => JSON.stringify(preview.value, null, 2))

function notify(text: string, type: typeof messageType.value = 'info') {
  message.value = text
  messageType.value = type
  snackbar.value = true
}

async function refresh() {
  ;[preview.value, consent.value] = await Promise.all([
    window.melDiagnostics.preview(),
    window.melDiagnostics.consent.get(),
  ])
}

async function perform(name: string, operation: () => Promise<unknown>, success: string) {
  busy.value = name
  try {
    await operation()
    await refresh()
    notify(success, 'success')
  } catch (error) {
    notify(error instanceof Error ? error.message : String(error), 'error')
  } finally {
    busy.value = ''
  }
}

async function saveConsent() {
  if (!consent.value) return
  await perform('consent', async () => {
    consent.value = await window.melDiagnostics.consent.set(consent.value!.enabled, consent.value!.endpoint)
  }, consent.value.enabled ? 'Remote diagnostics opt-in saved.' : 'Remote diagnostics remain disabled.')
}

async function createBundle() {
  await perform('bundle', async () => {
    const result = await window.melDiagnostics.createBundle(outputDirectory.value)
    await window.mel.revealPath(result.bundlePath)
  }, 'Redacted support bundle and SHA manifest created.')
}

async function send() {
  await perform('send', async () => { await window.melDiagnostics.send() }, 'The previewed diagnostics payload was sent.')
}

onMounted(async () => {
  const info = await window.mel.systemInfo()
  outputDirectory.value = info.downloadsPath
  await refresh()
})
</script>

<template>
  <div class="page-wrap">
    <PageHeader
      eyebrow="Support & Privacy"
      title="Preview every byte before it leaves"
      subtitle="Diagnostics exclude media, prompts, job configuration, credentials and raw paths. Remote telemetry is disabled until an HTTPS endpoint is explicitly enabled."
      icon="mdi-shield-account-outline"
      color="secondary"
    />

    <v-row>
      <v-col cols="12" lg="5">
        <v-card class="glass pa-6 h-100">
          <div class="text-overline text-secondary">Consent</div>
          <div class="text-h6 font-weight-bold mb-4">Default-off remote diagnostics</div>
          <v-switch v-if="consent" v-model="consent.enabled" color="secondary" label="Allow manual remote diagnostics sends" />
          <v-text-field
            v-if="consent"
            v-model="consent.endpoint"
            label="HTTPS diagnostics endpoint"
            prepend-inner-icon="mdi-webhook"
            :disabled="!consent.enabled"
            hint="Credentials, query strings and URL fragments are rejected or stripped."
            persistent-hint
          />
          <div class="d-flex flex-wrap ga-2 mt-5">
            <v-btn color="secondary" prepend-icon="mdi-content-save-outline" :loading="busy === 'consent'" @click="saveConsent">Save consent</v-btn>
            <v-btn color="primary" prepend-icon="mdi-send-check-outline" :disabled="!consent?.enabled" :loading="busy === 'send'" @click="send">Send preview</v-btn>
          </div>
          <v-alert type="warning" variant="tonal" class="mt-5">
            The application never sends diagnostics automatically. Each send re-generates the same redacted preview visible on this page.
          </v-alert>
        </v-card>
      </v-col>

      <v-col cols="12" lg="7">
        <v-card class="glass pa-6 h-100">
          <div class="text-overline text-primary">Local support bundle</div>
          <div class="text-h6 font-weight-bold mb-4">Compressed JSON + SHA-256 manifest</div>
          <PathField v-model="outputDirectory" label="Support bundle output directory" />
          <v-btn color="primary" prepend-icon="mdi-archive-lock-outline" :disabled="!outputDirectory" :loading="busy === 'bundle'" @click="createBundle">Create redacted bundle</v-btn>
          <v-list bg-color="transparent" density="compact" class="mt-4">
            <v-list-item prepend-icon="mdi-check" title="App, Electron, Node and platform versions" />
            <v-list-item prepend-icon="mdi-check" title="Database integrity and schema version" />
            <v-list-item prepend-icon="mdi-check" title="Job states without IDs, configs, prompts or paths" />
            <v-list-item prepend-icon="mdi-check" title="Engine capability summary without file paths" />
            <v-list-item prepend-icon="mdi-close" title="No media, API keys, credentials or raw project content" />
          </v-list>
        </v-card>
      </v-col>
    </v-row>

    <v-card class="glass pa-6 mt-6">
      <div class="d-flex align-center justify-space-between ga-3 mb-4">
        <div><div class="text-overline text-primary">Payload preview</div><div class="text-h6 font-weight-bold">Exact redacted structure</div></div>
        <v-btn variant="tonal" prepend-icon="mdi-refresh" :loading="busy === 'refresh'" @click="perform('refresh', refresh, 'Preview refreshed.')">Refresh</v-btn>
      </div>
      <pre class="diagnostics-preview" tabindex="0">{{ previewJson }}</pre>
    </v-card>

    <v-snackbar v-model="snackbar" :color="messageType" :timeout="6500">{{ message }}</v-snackbar>
  </div>
</template>

<style scoped>
.diagnostics-preview {
  max-height: 520px;
  overflow: auto;
  padding: 18px;
  border-radius: 14px;
  background: rgba(9, 15, 30, 0.92);
  color: #dbe4ff;
  font: 12px/1.55 ui-monospace, SFMono-Regular, Consolas, monospace;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
