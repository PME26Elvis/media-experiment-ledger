<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { DatabaseIntegrityResult, RecoveryBackupSummary, SystemInfo, UpdateStatus } from '../../shared/contracts'
import PageHeader from '../components/PageHeader.vue'
import PathField from '../components/PathField.vue'

const system = ref<SystemInfo>()
const status = ref<UpdateStatus>()
const integrity = ref<DatabaseIntegrityResult>()
const backups = ref<RecoveryBackupSummary[]>([])
const offlineManifest = ref('')
const offlinePackage = ref('')
const backupReason = ref('Manual recovery checkpoint')
const busy = ref('')
const message = ref('')
const messageType = ref<'success' | 'info' | 'warning' | 'error'>('info')
const snackbar = ref(false)

const stateColor = computed(() => {
  if (status.value?.state === 'error') return 'error'
  if (['available', 'downloaded', 'offline-staged'].includes(status.value?.state ?? '')) return 'success'
  if (status.value?.state === 'manual') return 'warning'
  return 'primary'
})
const stateIcon = computed(() => {
  if (status.value?.state === 'error') return 'mdi-alert-circle-outline'
  if (status.value?.state === 'downloaded' || status.value?.state === 'offline-staged') return 'mdi-package-variant-closed-check'
  if (status.value?.state === 'available') return 'mdi-cloud-download-outline'
  if (status.value?.state === 'manual') return 'mdi-open-in-new'
  return 'mdi-update'
})

function notify(text: string, type: typeof messageType.value = 'info') {
  message.value = text
  messageType.value = type
  snackbar.value = true
}

async function refresh() {
  ;[system.value, status.value, integrity.value, backups.value] = await Promise.all([
    window.mel.systemInfo(),
    window.mel.updater.status(),
    window.mel.recovery.integrity(),
    window.mel.recovery.list(),
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

async function check() {
  await perform('check', async () => { status.value = await window.mel.updater.check() }, 'Update check completed.')
}
async function download() {
  await perform('download', async () => { status.value = await window.mel.updater.download() }, 'Update downloaded and verified.')
}
async function installOnline() {
  await perform('install', async () => { await window.mel.updater.install() }, 'Installer is starting after a recovery backup.')
}
async function importOffline() {
  if (!offlineManifest.value || !offlinePackage.value) return
  await perform('offline', async () => {
    status.value = await window.mel.updater.importOffline(offlineManifest.value, offlinePackage.value)
  }, 'Offline update passed manifest, platform, size and SHA verification.')
}
async function openOffline() {
  await perform('open-offline', async () => { await window.mel.updater.openOffline() }, 'Verified offline installer opened after a recovery backup.')
}
async function createBackup() {
  await perform('backup', async () => { await window.mel.recovery.create(backupReason.value) }, 'Recovery backup created and hash verified.')
}
async function restore(backup: RecoveryBackupSummary) {
  await perform(`restore-${backup.id}`, async () => { await window.mel.recovery.restore(backup.id) }, 'Restore scheduled. The application will restart.')
}
async function remove(backup: RecoveryBackupSummary) {
  await perform(`remove-${backup.id}`, async () => { await window.mel.recovery.remove(backup.id) }, 'Recovery backup removed.')
}
async function revealBackup(backup: RecoveryBackupSummary) {
  await window.mel.revealPath(backup.manifestPath)
}

onMounted(refresh)
</script>

<template>
  <div class="page-wrap">
    <PageHeader eyebrow="Update & Recovery Center" title="Verified upgrades with a way back" subtitle="Online and offline update packages are gated by active jobs, platform identity, hashes and recovery checkpoints. Restores run before SQLite opens." icon="mdi-update" />

    <v-row>
      <v-col cols="12" lg="7">
        <v-card class="glass pa-6 h-100">
          <div class="d-flex flex-wrap align-center justify-space-between ga-3 mb-5">
            <div>
              <div class="text-overline text-primary">Application update</div>
              <div class="text-h5 font-weight-bold">{{ status?.currentVersion ?? 'Loading…' }}</div>
            </div>
            <v-chip :color="stateColor" :prepend-icon="stateIcon" variant="tonal">{{ status?.state ?? 'loading' }}</v-chip>
          </div>
          <v-alert v-if="status?.warning" type="warning" variant="tonal" class="mb-4">{{ status.warning }}</v-alert>
          <v-alert v-if="status?.error" type="error" variant="tonal" class="mb-4">{{ status.error }}</v-alert>
          <v-list bg-color="transparent" density="compact" class="mb-4">
            <v-list-item title="Current version" :subtitle="status?.currentVersion" prepend-icon="mdi-tag-outline" />
            <v-list-item title="Available version" :subtitle="status?.availableVersion ?? 'None detected'" prepend-icon="mdi-new-box" />
            <v-list-item title="Channel" :subtitle="status?.channel" prepend-icon="mdi-routes" />
            <v-list-item title="Platform mode" :subtitle="system?.updateMode === 'automatic' ? 'Automatic updater' : 'Signed manual packages'" prepend-icon="mdi-laptop" />
          </v-list>
          <v-progress-linear v-if="status?.state === 'downloading'" :model-value="status.progress ?? 0" color="primary" rounded height="10" class="mb-4" />
          <div class="d-flex flex-wrap ga-2">
            <v-btn color="primary" prepend-icon="mdi-refresh" :loading="busy === 'check'" @click="check">Check</v-btn>
            <v-btn v-if="status?.state === 'available'" color="secondary" prepend-icon="mdi-cloud-download-outline" :loading="busy === 'download'" @click="download">Download</v-btn>
            <v-btn v-if="status?.state === 'downloaded'" color="success" prepend-icon="mdi-restart-alert" :loading="busy === 'install'" @click="installOnline">Back up & install</v-btn>
          </div>
        </v-card>
      </v-col>

      <v-col cols="12" lg="5">
        <v-card class="glass pa-6 h-100">
          <div class="text-overline text-secondary">Offline package</div>
          <div class="text-h6 font-weight-bold mb-4">Air-gapped update staging</div>
          <PathField v-model="offlineManifest" kind="file" :extensions="['json']" label="Offline update manifest" hint="Stable manifests require an Ed25519 signature." />
          <PathField v-model="offlinePackage" kind="file" :extensions="['exe', 'msi', 'dmg', 'zip', 'AppImage', 'deb']" label="Matching installer package" />
          <div class="d-flex flex-wrap ga-2">
            <v-btn color="secondary" prepend-icon="mdi-package-down" :disabled="!offlineManifest || !offlinePackage" :loading="busy === 'offline'" @click="importOffline">Verify & stage</v-btn>
            <v-btn v-if="status?.state === 'offline-staged'" color="success" prepend-icon="mdi-package-up" :loading="busy === 'open-offline'" @click="openOffline">Back up & open</v-btn>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-1">
      <v-col cols="12" lg="4">
        <v-card class="glass pa-6 h-100">
          <div class="text-overline text-primary">Database health</div>
          <div class="d-flex align-center ga-3 mt-2">
            <v-avatar :color="integrity?.ok ? 'success' : 'error'" variant="tonal"><v-icon :icon="integrity?.ok ? 'mdi-database-check-outline' : 'mdi-database-alert-outline'" /></v-avatar>
            <div>
              <div class="text-h6 font-weight-bold">{{ integrity?.ok ? 'Integrity verified' : 'Attention required' }}</div>
              <div class="text-caption text-medium-emphasis">Schema {{ integrity?.schemaVersion ?? '…' }}</div>
            </div>
          </div>
          <v-chip v-for="item in integrity?.messages ?? []" :key="item" class="mt-4 mr-2" size="small" variant="tonal">{{ item }}</v-chip>
        </v-card>
      </v-col>

      <v-col cols="12" lg="8">
        <v-card class="glass pa-6 h-100">
          <div class="d-flex flex-wrap align-start justify-space-between ga-3 mb-4">
            <div><div class="text-overline text-secondary">Recovery checkpoints</div><div class="text-h6 font-weight-bold">Hash-verified application state</div></div>
            <div class="d-flex ga-2 align-center flex-grow-1" style="max-width: 560px">
              <v-text-field v-model="backupReason" label="Backup reason" density="compact" hide-details />
              <v-btn color="secondary" prepend-icon="mdi-content-save-check-outline" :loading="busy === 'backup'" @click="createBackup">Create</v-btn>
            </div>
          </div>
          <v-alert v-if="!backups.length" variant="tonal" type="info">No recovery backups yet.</v-alert>
          <v-list v-else bg-color="transparent" lines="three">
            <v-list-item v-for="backup in backups" :key="backup.id" :title="backup.reason">
              <template #prepend><v-avatar :color="backup.verified ? 'success' : 'error'" variant="tonal"><v-icon :icon="backup.verified ? 'mdi-shield-check-outline' : 'mdi-shield-alert-outline'" /></v-avatar></template>
              <template #subtitle><span>{{ backup.createdAt }} · v{{ backup.appVersion }} · {{ backup.fileCount }} files · {{ (backup.totalBytes / 1048576).toFixed(1) }} MiB</span></template>
              <template #append>
                <div class="d-flex ga-1">
                  <v-btn icon="mdi-folder-open-outline" variant="text" color="secondary" @click="revealBackup(backup)" />
                  <v-btn icon="mdi-backup-restore" variant="tonal" color="warning" :disabled="!backup.verified" :loading="busy === `restore-${backup.id}`" @click="restore(backup)" />
                  <v-btn icon="mdi-delete-outline" variant="text" color="error" :loading="busy === `remove-${backup.id}`" @click="remove(backup)" />
                </div>
              </template>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>

    <v-snackbar v-model="snackbar" :color="messageType" :timeout="6500">{{ message }}</v-snackbar>
  </div>
</template>
