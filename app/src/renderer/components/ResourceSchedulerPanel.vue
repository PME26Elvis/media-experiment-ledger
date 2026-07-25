<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type {
  DeviceResourcePolicy,
  ResourceSchedulerPreferences,
  ResourceSchedulerSnapshot,
} from '../../shared/resource-scheduler-contracts'

const snapshot = ref<ResourceSchedulerSnapshot>()
const preferences = ref<ResourceSchedulerPreferences>()
const selectedResource = ref('directml:0')
const selectedPolicy = ref<DeviceResourcePolicy>({ maxConcurrent: 1, memoryBudgetMb: 4096, safetyReserveMb: 512 })
const busy = ref(false)
const message = ref('')
const snackbar = ref(false)
let timer: ReturnType<typeof setInterval> | undefined

const acceleratorResources = computed(() => {
  const values = new Set(['directml:0', 'cuda:0', 'coreml:0'])
  for (const item of snapshot.value?.resources ?? []) if (item.accelerator) values.add(item.resourceKey)
  for (const key of Object.keys(preferences.value?.devicePolicies ?? {})) values.add(key)
  return [...values].sort()
})

function loadSelectedPolicy() {
  if (!preferences.value) return
  selectedPolicy.value = { ...(preferences.value.devicePolicies[selectedResource.value] ?? preferences.value.defaultAcceleratorPolicy) }
}

function bytesMb(value: number) {
  return value >= 1024 ? `${(value / 1024).toFixed(1)} GB` : `${value} MB`
}

async function refresh() {
  snapshot.value = await window.melResourceScheduler.snapshot()
  preferences.value ??= await window.melResourceScheduler.preferences.get()
  loadSelectedPolicy()
}

async function save() {
  if (!preferences.value) return
  busy.value = true
  try {
    const devicePolicies = {
      ...preferences.value.devicePolicies,
      [selectedResource.value]: { ...selectedPolicy.value },
    }
    preferences.value = await window.melResourceScheduler.preferences.set({
      cpuMaxConcurrent: preferences.value.cpuMaxConcurrent,
      warmSessionIdleSeconds: preferences.value.warmSessionIdleSeconds,
      defaultAcceleratorPolicy: preferences.value.defaultAcceleratorPolicy,
      devicePolicies,
    })
    await refresh()
    message.value = 'Resource policy saved. Queued jobs were re-evaluated immediately.'
    snackbar.value = true
  } finally { busy.value = false }
}

async function removeOverride() {
  if (!preferences.value) return
  const devicePolicies = { ...preferences.value.devicePolicies }
  delete devicePolicies[selectedResource.value]
  preferences.value = await window.melResourceScheduler.preferences.set({ devicePolicies })
  loadSelectedPolicy()
  await refresh()
  message.value = 'Device override removed; the default accelerator policy now applies.'
  snackbar.value = true
}

onMounted(async () => {
  preferences.value = await window.melResourceScheduler.preferences.get()
  await refresh()
  timer = setInterval(() => { void refresh() }, 2000)
})
onBeforeUnmount(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <v-card class="glass pa-6 mt-6">
    <div class="d-flex flex-wrap justify-space-between align-start ga-3 mb-5">
      <div>
        <div class="text-overline text-secondary">Resource-aware Job Scheduler</div>
        <div class="text-h6 font-weight-bold">Admission control before process creation</div>
        <div class="text-body-2 text-medium-emphasis mt-1">Jobs reserve a CPU slot or a provider/device memory budget before the engine starts. The queue explains exactly which limit is blocking it.</div>
      </div>
      <v-chip color="secondary" variant="tonal" prepend-icon="mdi-thermometer-lines">{{ snapshot?.reservations.length ?? 0 }} active reservations</v-chip>
    </div>

    <v-row v-if="preferences">
      <v-col cols="12" sm="6" md="3"><v-text-field v-model.number="preferences.cpuMaxConcurrent" type="number" min="1" max="64" label="CPU concurrent jobs" prepend-inner-icon="mdi-cpu-64-bit" /></v-col>
      <v-col cols="12" sm="6" md="3"><v-text-field v-model.number="preferences.warmSessionIdleSeconds" type="number" min="0" max="3600" label="Warm worker idle seconds" prepend-inner-icon="mdi-timer-sand" hint="0 closes the worker immediately" persistent-hint /></v-col>
      <v-col cols="12" sm="6" md="2"><v-text-field v-model.number="preferences.defaultAcceleratorPolicy.maxConcurrent" type="number" min="1" max="32" label="Default GPU concurrency" /></v-col>
      <v-col cols="12" sm="6" md="2"><v-text-field v-model.number="preferences.defaultAcceleratorPolicy.memoryBudgetMb" type="number" min="256" label="Default budget MB" /></v-col>
      <v-col cols="12" sm="6" md="2"><v-text-field v-model.number="preferences.defaultAcceleratorPolicy.safetyReserveMb" type="number" min="0" label="Default reserve MB" /></v-col>
    </v-row>

    <v-divider class="my-4" />
    <div class="text-subtitle-1 font-weight-bold mb-3">Provider/device override</div>
    <v-row>
      <v-col cols="12" md="3"><v-select v-model="selectedResource" :items="acceleratorResources" label="Resource key" prepend-inner-icon="mdi-expansion-card-variant" @update:model-value="loadSelectedPolicy" /></v-col>
      <v-col cols="12" md="3"><v-text-field v-model.number="selectedPolicy.maxConcurrent" type="number" min="1" max="32" label="Max concurrent" /></v-col>
      <v-col cols="12" md="3"><v-text-field v-model.number="selectedPolicy.memoryBudgetMb" type="number" min="256" label="Declared memory budget MB" /></v-col>
      <v-col cols="12" md="3"><v-text-field v-model.number="selectedPolicy.safetyReserveMb" type="number" min="0" label="Safety reserve MB" /></v-col>
    </v-row>
    <div class="d-flex flex-wrap ga-2">
      <v-btn color="secondary" prepend-icon="mdi-content-save-outline" :loading="busy" @click="save">Save scheduler policy</v-btn>
      <v-btn variant="tonal" prepend-icon="mdi-restore" :disabled="!preferences?.devicePolicies[selectedResource]" @click="removeOverride">Use default policy</v-btn>
    </div>
    <v-alert type="info" variant="tonal" density="compact" class="mt-4">Memory values are conservative admission budgets, not a claim that every operating system exposes exact free VRAM. Hardware evidence and real OOM errors remain visible separately.</v-alert>

    <v-row class="mt-3">
      <v-col v-for="resource in snapshot?.resources ?? []" :key="resource.resourceKey" cols="12" md="4">
        <v-card variant="tonal" class="pa-4 h-100">
          <div class="d-flex justify-space-between align-center"><div class="font-weight-bold">{{ resource.resourceKey }}</div><v-chip size="small" :color="resource.activeConcurrent ? 'success' : 'default'" variant="tonal">{{ resource.activeConcurrent }}/{{ resource.maxConcurrent }}</v-chip></div>
          <template v-if="resource.accelerator"><div class="text-body-2 mt-3">Reserved {{ bytesMb(resource.reservedMemoryMb) }} · available {{ bytesMb(resource.availableMemoryMb) }}</div><v-progress-linear class="mt-2" rounded height="8" color="secondary" :model-value="resource.memoryBudgetMb ? (resource.reservedMemoryMb + resource.safetyReserveMb) / resource.memoryBudgetMb * 100 : 0" /><div class="text-caption text-medium-emphasis mt-2">Budget {{ bytesMb(resource.memoryBudgetMb) }} · safety reserve {{ bytesMb(resource.safetyReserveMb) }}</div></template>
          <div v-else class="text-body-2 text-medium-emphasis mt-3">CPU jobs are governed by concurrent slots.</div>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-1">
      <v-col cols="12" lg="7">
        <div class="text-subtitle-1 font-weight-bold mb-3">Queued by resource policy</div>
        <v-list v-if="snapshot?.queued.length" bg-color="transparent" class="rounded-lg border-sm">
          <v-list-item v-for="item in snapshot.queued" :key="item.jobId" prepend-icon="mdi-timer-sand">
            <v-list-item-title>{{ item.title }}</v-list-item-title>
            <v-list-item-subtitle>{{ item.decision.reason ?? 'Ready to start' }} · estimate {{ item.decision.request.estimatedMemoryMb }} MB ({{ item.decision.request.estimateSource }})</v-list-item-subtitle>
          </v-list-item>
        </v-list>
        <v-alert v-else color="success" variant="tonal" density="compact">No jobs are waiting for a resource budget.</v-alert>
      </v-col>
      <v-col cols="12" lg="5">
        <div class="text-subtitle-1 font-weight-bold mb-3">Warm detection workers</div>
        <v-list v-if="snapshot?.warmWorkers?.length" bg-color="transparent" class="rounded-lg border-sm">
          <v-list-item v-for="worker in snapshot.warmWorkers" :key="worker.key" prepend-icon="mdi-fire-circle">
            <v-list-item-title>{{ worker.busy ? 'Busy worker' : 'Warm idle worker' }}</v-list-item-title>
            <v-list-item-subtitle class="text-truncate">{{ worker.key }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
        <v-alert v-else color="info" variant="tonal" density="compact">No warm worker is retained. A compatible Detection job creates one on demand.</v-alert>
      </v-col>
    </v-row>
    <v-snackbar v-model="snackbar" color="success" :timeout="5000">{{ message }}</v-snackbar>
  </v-card>
</template>
