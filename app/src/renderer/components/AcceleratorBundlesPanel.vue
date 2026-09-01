<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { AcceleratorBundleRecord, AcceleratorBundleSnapshot } from '../../shared/accelerator-bundle-contracts'

const snapshot = ref<AcceleratorBundleSnapshot>()
const busy = ref('')
const message = ref('')
const messageType = ref<'success' | 'info' | 'warning' | 'error'>('info')
const snackbar = ref(false)

const activeLabel = computed(() => snapshot.value?.active
  ? `${snapshot.value.active.profile} · ${snapshot.value.active.bundleId}@${snapshot.value.active.version}`
  : 'Universal CPU engine')

function notify(text: string, type: typeof messageType.value = 'info') {
  message.value = text
  messageType.value = type
  snackbar.value = true
}

async function refresh() {
  busy.value = 'refresh'
  try { snapshot.value = await window.melAcceleratorBundles.snapshot(true) }
  catch (error) { notify(error instanceof Error ? error.message : String(error), 'error') }
  finally { busy.value = '' }
}

async function install() {
  const manifestPath = await window.mel.chooseFile({ title: 'Select accelerator-bundle-manifest.json', extensions: ['json'] })
  if (!manifestPath) return
  busy.value = 'install'
  try {
    const record = await window.melAcceleratorBundles.install(manifestPath)
    snapshot.value = await window.melAcceleratorBundles.snapshot(true)
    notify(`Verified and installed ${record.bundleId}@${record.version}.`, 'success')
  } catch (error) { notify(error instanceof Error ? error.message : String(error), 'error') }
  finally { busy.value = '' }
}

async function activate(record: AcceleratorBundleRecord) {
  busy.value = `activate:${record.bundleId}:${record.version}`
  try {
    snapshot.value = await window.melAcceleratorBundles.activate(record.bundleId, record.version)
    notify(`${record.profile} bundle activated. New engine workers will use it.`, 'success')
  } catch (error) { notify(error instanceof Error ? error.message : String(error), 'error') }
  finally { busy.value = '' }
}

async function rollback() {
  busy.value = 'rollback'
  try {
    snapshot.value = await window.melAcceleratorBundles.rollback()
    notify(`Engine runtime rolled back to ${activeLabel.value}.`, 'success')
  } catch (error) { notify(error instanceof Error ? error.message : String(error), 'error') }
  finally { busy.value = '' }
}

async function quarantine(record: AcceleratorBundleRecord) {
  busy.value = `quarantine:${record.bundleId}:${record.version}`
  try {
    snapshot.value = await window.melAcceleratorBundles.quarantine(record.bundleId, record.version, 'Quarantined by the operator from Hardware Runtime Center.')
    notify(`${record.bundleId}@${record.version} moved to quarantine.`, 'warning')
  } catch (error) { notify(error instanceof Error ? error.message : String(error), 'error') }
  finally { busy.value = '' }
}

async function remove(record: AcceleratorBundleRecord) {
  busy.value = `remove:${record.bundleId}:${record.version}`
  try {
    snapshot.value = await window.melAcceleratorBundles.remove(record.bundleId, record.version)
    notify(`${record.bundleId}@${record.version} removed.`, 'success')
  } catch (error) { notify(error instanceof Error ? error.message : String(error), 'error') }
  finally { busy.value = '' }
}

onMounted(refresh)
</script>

<template>
  <v-card class="glass pa-6 mt-6">
    <div class="d-flex flex-wrap justify-space-between align-center ga-3 mb-4">
      <div>
        <div class="text-overline text-accent">Optional accelerator engines</div>
        <div class="text-h6 font-weight-bold">Signed, hash-pinned runtime bundles</div>
        <div class="text-medium-emphasis mt-1">Active runtime: {{ activeLabel }}</div>
      </div>
      <div class="d-flex flex-wrap ga-2">
        <v-btn color="primary" prepend-icon="mdi-package-down" :loading="busy === 'install'" @click="install">Install manifest</v-btn>
        <v-btn color="secondary" prepend-icon="mdi-backup-restore" :disabled="!snapshot?.active" :loading="busy === 'rollback'" @click="rollback">Rollback</v-btn>
        <v-btn variant="tonal" prepend-icon="mdi-refresh" :loading="busy === 'refresh'" @click="refresh">Refresh</v-btn>
      </div>
    </div>

    <v-alert type="info" variant="tonal" density="compact" class="mb-4">
      The base application always retains its universal CPU engine. A bundle is activated only after Ed25519 verification, per-file SHA-256 verification, host compatibility checks and a real packaged provider inventory self-test.
    </v-alert>
    <v-alert v-for="warning in snapshot?.warnings ?? []" :key="warning" type="warning" variant="tonal" density="compact" class="mb-3">{{ warning }}</v-alert>

    <v-row class="mb-2">
      <v-col cols="12" md="3"><v-card variant="tonal" class="pa-4 h-100"><div class="text-caption text-medium-emphasis">Host</div><div class="font-weight-bold">{{ snapshot?.host.platform }}/{{ snapshot?.host.arch }}</div><div class="text-caption">OS {{ snapshot?.host.osVersion ?? 'unknown' }}</div></v-card></v-col>
      <v-col cols="12" md="3"><v-card variant="tonal" class="pa-4 h-100"><div class="text-caption text-medium-emphasis">Studio</div><div class="font-weight-bold">{{ snapshot?.host.appVersion ?? 'unknown' }}</div><div class="text-caption">Compatibility is checked before copying</div></v-card></v-col>
      <v-col cols="12" md="3"><v-card variant="tonal" class="pa-4 h-100"><div class="text-caption text-medium-emphasis">NVIDIA driver</div><div class="font-weight-bold">{{ snapshot?.host.nvidiaDriver ?? 'Not detected' }}</div><div class="text-caption">Required only by CUDA profiles</div></v-card></v-col>
      <v-col cols="12" md="3"><v-card variant="tonal" class="pa-4 h-100"><div class="text-caption text-medium-emphasis">Trust anchor</div><div class="font-weight-bold text-truncate">{{ snapshot?.trustKeyPath ? 'Installed' : 'Missing' }}</div><div class="text-caption">Fail-closed when unavailable</div></v-card></v-col>
    </v-row>

    <div class="text-subtitle-1 font-weight-bold mt-5 mb-2">Installed bundles</div>
    <v-table density="comfortable" class="rounded-lg">
      <thead><tr><th>Bundle</th><th>Profile</th><th>Runtime</th><th>Evidence</th><th class="text-right">Actions</th></tr></thead>
      <tbody>
        <tr v-for="record in snapshot?.installed ?? []" :key="`${record.bundleId}:${record.version}`">
          <td><div class="font-weight-medium">{{ record.bundleId }}</div><div class="text-caption text-medium-emphasis">{{ record.version }} · {{ record.platform }}/{{ record.arch }}</div></td>
          <td><v-chip :color="record.state === 'active' ? 'success' : 'secondary'" size="small" variant="tonal">{{ record.profile }}{{ record.state === 'active' ? ' · active' : '' }}</v-chip></td>
          <td>ORT {{ record.manifest.engine.onnxRuntimeVersion }}<div class="text-caption">{{ record.manifest.engine.requiredProviders.join(', ') }}</div></td>
          <td><v-chip :color="record.verification?.signatureVerified && record.verification?.providerSelfTestPassed ? 'success' : 'warning'" size="small" variant="tonal">{{ record.verification?.filesVerified ?? 0 }} files verified</v-chip></td>
          <td class="text-right">
            <v-btn size="small" color="primary" variant="tonal" class="mr-2" :disabled="record.state === 'active'" :loading="busy === `activate:${record.bundleId}:${record.version}`" @click="activate(record)">Activate</v-btn>
            <v-btn size="small" color="warning" variant="tonal" class="mr-2" :loading="busy === `quarantine:${record.bundleId}:${record.version}`" @click="quarantine(record)">Quarantine</v-btn>
            <v-btn size="small" color="error" variant="text" :disabled="record.state === 'active'" :loading="busy === `remove:${record.bundleId}:${record.version}`" @click="remove(record)">Remove</v-btn>
          </td>
        </tr>
        <tr v-if="!(snapshot?.installed.length)"><td colspan="5" class="text-center text-medium-emphasis py-6">No optional accelerator bundle is installed. The CPU engine remains available.</td></tr>
      </tbody>
    </v-table>

    <v-expansion-panels v-if="snapshot?.quarantined.length" class="mt-5" variant="accordion">
      <v-expansion-panel>
        <v-expansion-panel-title>Quarantine · {{ snapshot.quarantined.length }} bundle(s)</v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-list bg-color="transparent"><v-list-item v-for="record in snapshot.quarantined" :key="record.path" prepend-icon="mdi-shield-alert-outline"><v-list-item-title>{{ record.bundleId }}@{{ record.version }}</v-list-item-title><v-list-item-subtitle>{{ record.quarantineReason ?? 'Verification or activation failure' }}</v-list-item-subtitle></v-list-item></v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
    <v-snackbar v-model="snackbar" :color="messageType" :timeout="7000">{{ message }}</v-snackbar>
  </v-card>
</template>
