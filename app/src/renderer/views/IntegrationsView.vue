<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type {
  CloudSyncResult,
  GitHubPublishResult,
  SaveScheduleRequest,
  ScheduledJobDefinition,
  WasmPostprocessResult,
} from '../../shared/integration-contracts'
import type { JobKind, SecretProfileSummary } from '../../shared/contracts'
import PageHeader from '../components/PageHeader.vue'
import PathField from '../components/PathField.vue'

const { t } = useI18n()
const busy = ref(false)
const error = ref('')
const notice = ref('')
const schedules = ref<ScheduledJobDefinition[]>([])
const profiles = ref<SecretProfileSummary[]>([])
const syncResult = ref<CloudSyncResult>()
const publishResult = ref<GitHubPublishResult>()
const wasmResult = ref<WasmPostprocessResult>()

const schedule = reactive({
  name: 'Nightly import scan', enabled: true, cadenceKind: 'daily' as 'daily' | 'weekly' | 'interval',
  hour: 2, minute: 0, intervalHours: 24, weekdays: [1, 3, 5],
  jobKind: 'scan' as JobKind, jobTitle: 'Scheduled scan', configJson: '{}',
})
const sync = reactive({ projectRoot: '', syncRoot: '', dryRun: false })
const github = reactive({
  repository: '', tag: '', name: '', body: '', draft: true, prerelease: false,
  assets: '', credentialProfileId: '',
})
const wasm = reactive({ modulePath: '', sha256: '', inputJson: '{\n  "boxes": []\n}', timeoutMs: 1000, maxMemoryPages: 64 })

const unlockedGitHubProfiles = computed(() => profiles.value.filter(profile => profile.unlocked && profile.provider.toLowerCase().includes('github')))

onMounted(async () => {
  await refresh()
  profiles.value = await window.mel.secrets.list()
  github.credentialProfileId = unlockedGitHubProfiles.value[0]?.id ?? ''
})

async function action(operation: () => Promise<void>) {
  busy.value = true
  error.value = ''
  notice.value = ''
  try { await operation() } catch (value) { error.value = value instanceof Error ? value.message : String(value) }
  finally { busy.value = false }
}

async function refresh() {
  schedules.value = await window.melIntegrations.schedules.list()
}

function scheduleRequest(): SaveScheduleRequest {
  const config = JSON.parse(schedule.configJson) as Record<string, unknown>
  const cadence = schedule.cadenceKind === 'daily'
    ? { kind: 'daily' as const, hour: schedule.hour, minute: schedule.minute }
    : schedule.cadenceKind === 'weekly'
      ? { kind: 'weekly' as const, weekdays: schedule.weekdays, hour: schedule.hour, minute: schedule.minute }
      : { kind: 'interval' as const, hours: schedule.intervalHours }
  return {
    name: schedule.name,
    enabled: schedule.enabled,
    cadence,
    job: { kind: schedule.jobKind, title: schedule.jobTitle, config },
  }
}

async function saveSchedule() {
  await action(async () => {
    await window.melIntegrations.schedules.save(scheduleRequest())
    await refresh()
    notice.value = t('integrations.scheduleSaved')
  })
}

async function runSchedule(id: string) {
  await action(async () => {
    await window.melIntegrations.schedules.runNow(id)
    notice.value = t('integrations.scheduleQueued')
  })
}

async function removeSchedule(id: string) {
  await action(async () => {
    await window.melIntegrations.schedules.remove(id)
    await refresh()
  })
}

async function runSync() {
  await action(async () => {
    syncResult.value = await window.melIntegrations.sync.run(sync)
    notice.value = t('integrations.syncComplete')
  })
}

async function publish() {
  await action(async () => {
    publishResult.value = await window.melIntegrations.github.publish({
      repository: github.repository,
      tag: github.tag,
      name: github.name,
      body: github.body,
      draft: github.draft,
      prerelease: github.prerelease,
      assetPaths: github.assets.split(/\r?\n/u).map(value => value.trim()).filter(Boolean),
      credentialProfileId: github.credentialProfileId,
    })
    notice.value = t('integrations.releaseCreated')
  })
}

async function runWasm() {
  await action(async () => {
    wasmResult.value = await window.melIntegrations.wasm.postprocess({
      modulePath: wasm.modulePath,
      sha256: wasm.sha256,
      input: JSON.parse(wasm.inputJson),
      timeoutMs: wasm.timeoutMs,
      maxMemoryPages: wasm.maxMemoryPages,
    })
    notice.value = t('integrations.wasmComplete')
  })
}
</script>

<template>
  <div class="page-wrap">
    <PageHeader
      :eyebrow="t('integrations.eyebrow')"
      :title="t('integrations.title')"
      :subtitle="t('integrations.subtitle')"
      icon="mdi-connection"
    />
    <v-alert v-if="error" type="error" variant="tonal" class="mb-4" closable @click:close="error = ''">{{ error }}</v-alert>
    <v-alert v-if="notice" type="success" variant="tonal" class="mb-4" closable @click:close="notice = ''">{{ notice }}</v-alert>

    <v-row>
      <v-col cols="12" xl="6">
        <v-card class="glass pa-6 h-100">
          <div class="text-overline text-primary">{{ t('integrations.scheduler') }}</div>
          <div class="text-h5 mb-4">{{ t('integrations.schedulerTitle') }}</div>
          <v-row>
            <v-col cols="12" md="7"><v-text-field v-model="schedule.name" :label="t('integrations.name')" prepend-inner-icon="mdi-calendar-clock" /></v-col>
            <v-col cols="12" md="5"><v-switch v-model="schedule.enabled" color="primary" :label="t('integrations.enabled')" /></v-col>
            <v-col cols="12" md="4"><v-select v-model="schedule.cadenceKind" :label="t('integrations.cadence')" :items="['daily', 'weekly', 'interval']" /></v-col>
            <v-col v-if="schedule.cadenceKind !== 'interval'" cols="6" md="2"><v-text-field v-model.number="schedule.hour" type="number" label="Hour" /></v-col>
            <v-col v-if="schedule.cadenceKind !== 'interval'" cols="6" md="2"><v-text-field v-model.number="schedule.minute" type="number" label="Minute" /></v-col>
            <v-col v-if="schedule.cadenceKind === 'interval'" cols="12" md="4"><v-text-field v-model.number="schedule.intervalHours" type="number" :label="t('integrations.intervalHours')" /></v-col>
            <v-col v-if="schedule.cadenceKind === 'weekly'" cols="12" md="4"><v-select v-model="schedule.weekdays" multiple chips :label="t('integrations.weekdays')" :items="[0,1,2,3,4,5,6]" /></v-col>
            <v-col cols="12" md="4"><v-select v-model="schedule.jobKind" :label="t('integrations.jobKind')" :items="['scan','atlas','detection','automation','pdf-export','sample-download']" /></v-col>
            <v-col cols="12" md="8"><v-text-field v-model="schedule.jobTitle" :label="t('integrations.jobTitle')" /></v-col>
            <v-col cols="12"><v-textarea v-model="schedule.configJson" label="Job config JSON" rows="3" spellcheck="false" /></v-col>
          </v-row>
          <v-btn color="primary" prepend-icon="mdi-calendar-plus" :loading="busy" @click="saveSchedule">{{ t('integrations.installSchedule') }}</v-btn>
          <v-divider class="my-5" />
          <v-list v-if="schedules.length" bg-color="transparent">
            <v-list-item v-for="item in schedules" :key="item.id" :title="item.name" :subtitle="`${item.backend} · ${item.cadence.kind}`">
              <template #append>
                <v-btn icon="mdi-play" variant="text" color="primary" :aria-label="t('common.run')" @click="runSchedule(item.id)" />
                <v-btn icon="mdi-delete-outline" variant="text" color="error" aria-label="Remove" @click="removeSchedule(item.id)" />
              </template>
            </v-list-item>
          </v-list>
          <v-alert v-else type="info" variant="tonal">{{ t('integrations.noSchedules') }}</v-alert>
        </v-card>
      </v-col>

      <v-col cols="12" xl="6">
        <v-card class="glass pa-6 h-100">
          <div class="text-overline text-primary">{{ t('integrations.sync') }}</div>
          <div class="text-h5 mb-4">{{ t('integrations.syncTitle') }}</div>
          <PathField v-model="sync.projectRoot" :label="t('integrations.projectRoot')" />
          <PathField v-model="sync.syncRoot" :label="t('integrations.syncRoot')" />
          <v-switch v-model="sync.dryRun" color="primary" :label="t('integrations.dryRun')" />
          <v-btn color="primary" prepend-icon="mdi-folder-sync-outline" :loading="busy" @click="runSync">{{ t('integrations.runSync') }}</v-btn>
          <v-card v-if="syncResult" variant="tonal" class="mt-4 pa-4">
            <div class="font-weight-bold">{{ syncResult.direction }} · {{ syncResult.snapshotId }}</div>
            <div class="text-body-2">↑ {{ syncResult.uploadedFiles }} · ↓ {{ syncResult.downloadedFiles }} · conflicts {{ syncResult.conflicts.length }}</div>
          </v-card>
        </v-card>
      </v-col>

      <v-col cols="12" xl="6">
        <v-card class="glass pa-6 h-100">
          <div class="text-overline text-primary">GitHub</div>
          <div class="text-h5 mb-4">{{ t('integrations.githubTitle') }}</div>
          <v-row>
            <v-col cols="12" md="7"><v-text-field v-model="github.repository" label="owner/repository" prepend-inner-icon="mdi-github" /></v-col>
            <v-col cols="12" md="5"><v-text-field v-model="github.tag" label="Tag" /></v-col>
            <v-col cols="12"><v-text-field v-model="github.name" :label="t('integrations.releaseName')" /></v-col>
            <v-col cols="12"><v-textarea v-model="github.body" :label="t('integrations.releaseBody')" rows="3" /></v-col>
            <v-col cols="12"><v-textarea v-model="github.assets" :label="t('integrations.assetPaths')" rows="4" spellcheck="false" /></v-col>
            <v-col cols="12" md="6"><v-select v-model="github.credentialProfileId" :label="t('integrations.credential')" :items="unlockedGitHubProfiles" item-title="name" item-value="id" /></v-col>
            <v-col cols="6" md="3"><v-switch v-model="github.draft" color="primary" label="Draft" /></v-col>
            <v-col cols="6" md="3"><v-switch v-model="github.prerelease" color="primary" label="Prerelease" /></v-col>
          </v-row>
          <v-alert variant="tonal" type="warning" class="mb-4">{{ t('integrations.immutableWarning') }}</v-alert>
          <v-btn color="primary" prepend-icon="mdi-cloud-upload-outline" :loading="busy" :disabled="!github.credentialProfileId" @click="publish">{{ t('integrations.publish') }}</v-btn>
          <v-card v-if="publishResult" variant="tonal" class="mt-4 pa-4">{{ publishResult.tag }} · {{ publishResult.uploadedAssets.length }} assets</v-card>
        </v-card>
      </v-col>

      <v-col cols="12" xl="6">
        <v-card class="glass pa-6 h-100">
          <div class="text-overline text-primary">WASM</div>
          <div class="text-h5 mb-4">{{ t('integrations.wasmTitle') }}</div>
          <PathField v-model="wasm.modulePath" :label="t('integrations.modulePath')" :extensions="['wasm']" mode="file" />
          <v-text-field v-model="wasm.sha256" label="Pinned SHA-256" prepend-inner-icon="mdi-fingerprint" />
          <v-textarea v-model="wasm.inputJson" label="Input JSON" rows="5" spellcheck="false" />
          <v-row>
            <v-col cols="6"><v-text-field v-model.number="wasm.timeoutMs" type="number" label="Timeout (ms)" /></v-col>
            <v-col cols="6"><v-text-field v-model.number="wasm.maxMemoryPages" type="number" label="Memory pages" /></v-col>
          </v-row>
          <v-alert type="info" variant="tonal" class="mb-4">{{ t('integrations.wasmPolicy') }}</v-alert>
          <v-btn color="primary" prepend-icon="mdi-shield-play-outline" :loading="busy" @click="runWasm">{{ t('integrations.runWasm') }}</v-btn>
          <pre v-if="wasmResult" class="mt-4 text-caption overflow-auto">{{ JSON.stringify(wasmResult, null, 2) }}</pre>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>
