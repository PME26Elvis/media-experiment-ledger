<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type {
  HardwarePreferences,
  HardwareProviderKey,
  HardwareSelfTestResult,
  HardwareSnapshot,
} from '../../shared/hardware-contracts'
import AcceleratorBundlesPanel from '../components/AcceleratorBundlesPanel.vue'
import PageHeader from '../components/PageHeader.vue'
import ResourceSchedulerPanel from '../components/ResourceSchedulerPanel.vue'

const { t } = useI18n()
const snapshot = ref<HardwareSnapshot>()
const preferences = ref<HardwarePreferences>({ provider: 'cpu', deviceId: 0, allowCpuFallback: true, coremlComputeUnits: 'ALL' })
const selfTest = ref<HardwareSelfTestResult>()
const busy = ref('')
const message = ref('')
const messageType = ref<'success' | 'info' | 'warning' | 'error'>('info')
const snackbar = ref(false)

const providers = computed(() => {
  const labels: Record<HardwareProviderKey, string> = { cpu: 'CPU', directml: 'DirectML', cuda: 'CUDA', coreml: 'CoreML' }
  return (Object.keys(labels) as HardwareProviderKey[]).map(key => {
    const support = snapshot.value?.engineProviders?.provider_support[key]
    return { key, label: labels[key], provider: support?.provider ?? 'unknown', available: support?.available === true }
  })
})
const providerItems = computed(() => providers.value.map(item => ({
  title: `${item.label}${item.available ? '' : ' · unavailable'}`, value: item.key, props: { disabled: !item.available },
})))
const selectedAvailable = computed(() => providers.value.find(item => item.key === preferences.value.provider)?.available === true)

function notify(text: string, type: typeof messageType.value = 'info') {
  message.value = text
  messageType.value = type
  snackbar.value = true
}
function bytes(value?: number) {
  if (!value || value <= 0) return 'Unknown'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let amount = value
  let index = 0
  while (amount >= 1024 && index < units.length - 1) { amount /= 1024; index += 1 }
  return `${amount.toFixed(index > 1 ? 1 : 0)} ${units[index]}`
}
async function refresh() {
  busy.value = 'refresh'
  try {
    snapshot.value = await window.melHardware.snapshot(true)
    if (!selectedAvailable.value) preferences.value.provider = 'cpu'
  } catch (error) { notify(error instanceof Error ? error.message : String(error), 'error') }
  finally { busy.value = '' }
}
async function savePreferences() {
  busy.value = 'save'
  try {
    preferences.value = await window.melHardware.preferences.set(preferences.value)
    notify('Hardware runtime preferences saved.', 'success')
  } catch (error) { notify(error instanceof Error ? error.message : String(error), 'error') }
  finally { busy.value = '' }
}
async function runSelfTest() {
  busy.value = 'test'
  selfTest.value = undefined
  try {
    selfTest.value = await window.melHardware.selfTest({ ...preferences.value, warmRuns: 5 })
    notify(selfTest.value.passed ? 'Provider self-test passed.' : 'Provider self-test completed with a warning or failure.', selfTest.value.passed ? 'success' : 'warning')
  } catch (error) { notify(error instanceof Error ? error.message : String(error), 'error') }
  finally { busy.value = '' }
}
async function clearCache() {
  busy.value = 'cache'
  try {
    const result = await window.melHardware.clearCache(preferences.value.provider)
    notify(`Provider cache cleared. Removed ${bytes(result.removedBytes)}.`, 'success')
  } catch (error) { notify(error instanceof Error ? error.message : String(error), 'error') }
  finally { busy.value = '' }
}
async function exportEvidence() {
  const directory = await window.mel.chooseDirectory()
  if (!directory) return
  busy.value = 'export'
  try {
    const result = await window.melHardware.exportEvidence(directory, selfTest.value)
    await window.mel.revealPath(result.path)
    notify('Redacted hardware evidence exported.', 'success')
  } catch (error) { notify(error instanceof Error ? error.message : String(error), 'error') }
  finally { busy.value = '' }
}

onMounted(async () => {
  ;[preferences.value, snapshot.value] = await Promise.all([window.melHardware.preferences.get(), window.melHardware.snapshot()])
  if (!selectedAvailable.value) preferences.value.provider = 'cpu'
})
</script>

<template>
  <div class="page-wrap">
    <PageHeader eyebrow="Hardware Runtime Center" :title="t('hardware.title')" :subtitle="t('hardware.subtitle')" icon="mdi-expansion-card-variant" color="secondary" />
    <div class="d-flex flex-wrap ga-2 mb-5">
      <v-btn color="primary" prepend-icon="mdi-refresh" :loading="busy === 'refresh'" @click="refresh">Refresh hardware</v-btn>
      <v-btn color="secondary" prepend-icon="mdi-file-export-outline" :loading="busy === 'export'" @click="exportEvidence">Export evidence</v-btn>
    </div>

    <v-row>
      <v-col cols="12" md="4"><v-card class="glass pa-5 h-100"><div class="text-overline text-primary">Host CPU</div><div class="text-h6 font-weight-bold">{{ snapshot?.cpu.model ?? 'Inspecting…' }}</div><div class="text-medium-emphasis mt-2">{{ snapshot?.cpu.logicalCores ?? 0 }} logical cores</div></v-card></v-col>
      <v-col cols="12" md="4"><v-card class="glass pa-5 h-100"><div class="text-overline text-secondary">System memory</div><div class="text-h6 font-weight-bold">{{ bytes(snapshot?.memory.totalBytes) }}</div><div class="text-medium-emphasis mt-2">{{ bytes(snapshot?.memory.freeBytes) }} currently free</div></v-card></v-col>
      <v-col cols="12" md="4"><v-card class="glass pa-5 h-100"><div class="text-overline text-accent">Packaged runtime</div><div class="text-h6 font-weight-bold">ONNX Runtime {{ snapshot?.engineProviders?.runtime_version ?? 'unavailable' }}</div><div class="text-medium-emphasis mt-2">{{ snapshot?.engineProviders?.runtime_device ?? 'No runtime device report' }}</div></v-card></v-col>
    </v-row>

    <v-row class="mt-1">
      <v-col cols="12" lg="7">
        <v-card class="glass pa-6 h-100">
          <div class="text-overline text-primary">Execution providers</div><div class="text-h6 font-weight-bold mb-4">Registration is not execution evidence</div>
          <v-table density="comfortable" class="rounded-lg"><thead><tr><th>Provider</th><th>Runtime name</th><th>Status</th></tr></thead><tbody><tr v-for="item in providers" :key="item.key"><td class="font-weight-medium">{{ item.label }}</td><td>{{ item.provider }}</td><td><v-chip :color="item.available ? 'success' : 'warning'" variant="tonal" size="small">{{ item.available ? 'Registered' : 'Unavailable' }}</v-chip></td></tr></tbody></v-table>
          <v-alert v-for="warning in snapshot?.warnings ?? []" :key="warning" type="warning" variant="tonal" density="compact" class="mt-4">{{ warning }}</v-alert>
        </v-card>
      </v-col>
      <v-col cols="12" lg="5">
        <v-card class="glass pa-6 h-100">
          <div class="text-overline text-secondary">Desktop GPU adapters</div><div class="text-h6 font-weight-bold mb-4">Electron / Chromium device view</div>
          <v-list v-if="snapshot?.gpuDevices.length" bg-color="transparent" lines="three"><v-list-item v-for="device in snapshot.gpuDevices" :key="device.id" prepend-icon="mdi-memory"><v-list-item-title>{{ device.name ?? `GPU adapter ${device.id}` }}</v-list-item-title><v-list-item-subtitle>{{ device.vendor ?? device.driverVendor ?? 'Unknown vendor' }} · device {{ device.deviceId ?? 'unknown' }} · driver {{ device.driverVersion ?? 'unknown' }}</v-list-item-subtitle><template #append><v-chip :color="device.active ? 'success' : 'default'" size="small" variant="tonal">{{ device.active ? 'Active' : 'Detected' }}</v-chip></template></v-list-item></v-list>
          <v-alert v-else color="info" variant="tonal">No discrete adapter metadata was reported. CPU and provider self-tests remain available.</v-alert>
        </v-card>
      </v-col>
    </v-row>

    <v-card class="glass pa-6 mt-6">
      <div class="text-overline text-primary">Production provider policy</div><div class="text-h6 font-weight-bold mb-4">Select, save, then prove the same planner</div>
      <v-row>
        <v-col cols="12" md="3"><v-select v-model="preferences.provider" :items="providerItems" label="Execution provider" prepend-inner-icon="mdi-expansion-card-variant" /></v-col>
        <v-col cols="12" md="2"><v-text-field v-model.number="preferences.deviceId" type="number" label="Device ID" :min="0" :max="64" prepend-inner-icon="mdi-identifier" /></v-col>
        <v-col cols="12" md="3"><v-select v-model="preferences.coremlComputeUnits" label="CoreML compute units" :items="['ALL', 'CPU_ONLY', 'CPU_AND_GPU', 'CPU_AND_NE']" :disabled="preferences.provider !== 'coreml'" prepend-inner-icon="mdi-apple" /></v-col>
        <v-col cols="12" md="4" class="d-flex align-center"><v-switch v-model="preferences.allowCpuFallback" color="secondary" label="Allow explicit CPU fallback" :disabled="preferences.provider === 'cpu'" hide-details /></v-col>
      </v-row>
      <div class="d-flex flex-wrap ga-2"><v-btn color="primary" prepend-icon="mdi-content-save-outline" :loading="busy === 'save'" @click="savePreferences">Save policy</v-btn><v-btn color="secondary" prepend-icon="mdi-play-circle-outline" :disabled="!selectedAvailable" :loading="busy === 'test'" @click="runSelfTest">Run provider self-test</v-btn><v-btn variant="tonal" prepend-icon="mdi-delete-sweep-outline" :loading="busy === 'cache'" @click="clearCache">Clear provider cache</v-btn></div>
    </v-card>

    <v-card v-if="selfTest" class="glass pa-6 mt-6">
      <div class="d-flex flex-wrap justify-space-between align-center ga-3"><div><div class="text-overline text-secondary">Self-test evidence</div><div class="text-h6 font-weight-bold">{{ selfTest.requested_provider_name }}</div></div><v-chip :color="selfTest.passed ? 'success' : selfTest.status === 'fallback' ? 'warning' : 'error'" variant="tonal">{{ selfTest.status }}</v-chip></div>
      <v-row class="mt-2"><v-col cols="6" md="2"><div class="text-caption text-medium-emphasis">Registered</div><div class="font-weight-bold">{{ selfTest.registered ? 'Yes' : 'No' }}</div></v-col><v-col cols="6" md="2"><div class="text-caption text-medium-emphasis">Session</div><div class="font-weight-bold">{{ selfTest.session_created ? 'Created' : 'Failed' }}</div></v-col><v-col cols="6" md="2"><div class="text-caption text-medium-emphasis">Assigned nodes</div><div class="font-weight-bold">{{ selfTest.assigned_node_count }}</div></v-col><v-col cols="6" md="2"><div class="text-caption text-medium-emphasis">CPU nodes</div><div class="font-weight-bold">{{ selfTest.cpu_assigned_node_count }}</div></v-col><v-col cols="6" md="2"><div class="text-caption text-medium-emphasis">Cold run</div><div class="font-weight-bold">{{ selfTest.cold_inference_ms ?? '—' }} ms</div></v-col><v-col cols="6" md="2"><div class="text-caption text-medium-emphasis">Warm average</div><div class="font-weight-bold">{{ selfTest.warm_inference_ms ?? '—' }} ms</div></v-col></v-row>
      <v-alert v-if="selfTest.recommendation" :type="selfTest.passed ? 'success' : 'warning'" variant="tonal" class="mt-3">{{ selfTest.recommendation }}</v-alert><v-alert v-if="selfTest.error" type="error" variant="tonal" class="mt-3">{{ selfTest.error.name }}: {{ selfTest.error.message }}</v-alert>
    </v-card>

    <AcceleratorBundlesPanel />
    <ResourceSchedulerPanel />
    <v-snackbar v-model="snackbar" :color="messageType" :timeout="6500">{{ message }}</v-snackbar>
  </div>
</template>
