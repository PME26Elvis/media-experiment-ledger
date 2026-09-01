<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import type { AppliedReportTemplate, CustomReportTemplateSummary } from '../../shared/template-contracts'

const props = defineProps<{ documentId?: string }>()
const emit = defineEmits<{ applied: [snapshot: AppliedReportTemplate] }>()
const templates = ref<CustomReportTemplateSummary[]>([])
const applied = ref<AppliedReportTemplate | null>(null)
const busy = ref('')
const message = ref('')
const snackbar = ref(false)

async function refresh() {
  templates.value = await window.melTemplates.list()
  applied.value = props.documentId ? await window.melTemplates.applied(props.documentId) : null
}

async function importTemplate() {
  const path = await window.mel.chooseFile({ title: 'Import MEL report template', extensions: ['json'] })
  if (!path) return
  busy.value = 'import'
  try {
    await window.melTemplates.import(path)
    message.value = 'Template schema validated and imported.'
    snackbar.value = true
    await refresh()
  } catch (error) {
    message.value = error instanceof Error ? error.message : String(error)
    snackbar.value = true
  } finally {
    busy.value = ''
  }
}

async function exportTemplate(template: CustomReportTemplateSummary) {
  const root = await window.mel.chooseDirectory()
  if (!root) return
  const path = await window.melTemplates.export(template.id, root)
  await window.mel.revealPath(path)
}

async function applyTemplate(template: CustomReportTemplateSummary) {
  if (!props.documentId) return
  busy.value = template.id
  try {
    const snapshot = await window.melTemplates.apply(props.documentId, template.id)
    applied.value = snapshot
    emit('applied', snapshot)
    message.value = `Applied immutable snapshot: ${snapshot.definition.name}`
    snackbar.value = true
  } finally {
    busy.value = ''
  }
}

async function removeTemplate(template: CustomReportTemplateSummary) {
  busy.value = `remove-${template.id}`
  try {
    await window.melTemplates.remove(template.id)
    message.value = 'Library template removed. Existing document snapshots remain unchanged.'
    snackbar.value = true
    await refresh()
  } finally {
    busy.value = ''
  }
}

watch(() => props.documentId, refresh)
onMounted(refresh)
</script>

<template>
  <v-card class="glass pa-5 mt-5">
    <div class="d-flex align-center justify-space-between ga-3 mb-4">
      <div>
        <div class="text-overline text-secondary">Custom templates</div>
        <div class="text-h6 font-weight-bold">Validated design snapshots</div>
      </div>
      <v-btn icon="mdi-import" color="secondary" variant="tonal" :loading="busy === 'import'" @click="importTemplate" />
    </div>
    <v-alert v-if="applied" type="success" variant="tonal" density="compact" class="mb-4">
      This document uses snapshot “{{ applied.definition.name }}” applied {{ applied.appliedAt }}.
    </v-alert>
    <v-alert v-if="!templates.length" type="info" variant="tonal" density="compact">
      Import a `.json` template containing only validated page, margin, font and color fields. HTML, scripts and CSS are not accepted.
    </v-alert>
    <v-list v-else bg-color="transparent" density="compact">
      <v-list-item v-for="template in templates" :key="template.id" :title="template.definition.name" :subtitle="template.definition.description">
        <template #prepend>
          <v-avatar :color="template.definition.colors.primary" size="34"><v-icon icon="mdi-palette-swatch-outline" /></v-avatar>
        </template>
        <template #append>
          <div class="d-flex ga-1">
            <v-btn icon="mdi-check" size="small" color="primary" variant="tonal" :disabled="!documentId" :loading="busy === template.id" @click="applyTemplate(template)" />
            <v-btn icon="mdi-export" size="small" variant="text" @click="exportTemplate(template)" />
            <v-btn icon="mdi-delete-outline" size="small" color="error" variant="text" :loading="busy === `remove-${template.id}`" @click="removeTemplate(template)" />
          </div>
        </template>
      </v-list-item>
    </v-list>
    <v-snackbar v-model="snackbar" :timeout="5000">{{ message }}</v-snackbar>
  </v-card>
</template>
