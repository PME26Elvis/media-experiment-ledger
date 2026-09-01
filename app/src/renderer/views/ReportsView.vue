<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type {
  ReportBlock,
  ReportDocument,
  ReportRevisionSummary,
  ReportSummary,
} from '../../shared/contracts'
import type { AppliedReportTemplate } from '../../shared/template-contracts'
import { REPORT_TEMPLATES, reportTemplate } from '../../shared/report-templates'
import PageHeader from '../components/PageHeader.vue'
import ReportBlockEditor from '../components/ReportBlockEditor.vue'
import ReportTemplateLibrary from '../components/ReportTemplateLibrary.vue'

const summaries = ref<ReportSummary[]>([])
const document = ref<ReportDocument>()
const selectedBlockId = ref('')
const tab = ref('editor')
const revisions = ref<ReportRevisionSummary[]>([])
const appliedTemplate = ref<AppliedReportTemplate | null>(null)
const saving = ref(false)
const message = ref('')
const snackbar = ref(false)
let autosaveTimer: number | undefined
let loadingDocument = false

const selectedBlock = computed(() => document.value?.blocks.find(block => block.id === selectedBlockId.value))
const pages = computed(() => Array.from({
  length: Math.max(1, ...(document.value?.blocks.map(block => block.layout.page) ?? [1])),
}, (_, index) => index + 1))
const currentTemplate = computed(() => {
  if (appliedTemplate.value) {
    return {
      name: appliedTemplate.value.definition.name,
      description: appliedTemplate.value.definition.description,
      page: appliedTemplate.value.definition.page,
      colors: appliedTemplate.value.definition.colors,
    }
  }
  const builtIn = document.value ? reportTemplate(document.value.template) : REPORT_TEMPLATES[0]
  return {
    name: builtIn.title,
    description: builtIn.description,
    page: builtIn.page,
    colors: builtIn.colors,
  }
})

function notify(text: string) {
  message.value = text
  snackbar.value = true
}

function uuid() {
  return crypto.randomUUID()
}

function defaultStyle() {
  return {
    fontFamily: 'sans' as const,
    fontSize: 18,
    fontWeight: 400 as const,
    italic: false,
    underline: false,
    alignment: 'left' as const,
    color: '#172033',
    lineHeight: 1.5,
  }
}

function defaultLayout(page = 1) {
  return {
    mode: 'structured' as const,
    span: 2 as const,
    page,
    x: 5,
    y: 5,
    width: 90,
    height: 12,
  }
}

async function refresh() {
  summaries.value = await window.mel.reports.list()
}

async function load(id: string) {
  loadingDocument = true
  try {
    document.value = await window.mel.reports.get(id)
    selectedBlockId.value = document.value.blocks[0]?.id ?? ''
    const [history, applied] = await Promise.all([
      window.mel.reports.revisions(id),
      window.melTemplates.applied(id),
    ])
    revisions.value = history
    appliedTemplate.value = applied
  } finally {
    loadingDocument = false
  }
}

async function create() {
  const created = await window.mel.reports.create('Untitled Atlas Report')
  await refresh()
  await load(created.id)
}

async function importAtlas() {
  const path = await window.mel.chooseFile({ title: 'Import atlas-manifest.json', extensions: ['json'] })
  if (!path) return
  try {
    const created = await window.mel.reports.importAtlas(path)
    await refresh()
    await load(created.id)
    notify('Atlas manifest imported into a new report document.')
  } catch (error) {
    notify(error instanceof Error ? error.message : String(error))
  }
}

function scheduleAutosave() {
  if (loadingDocument || !document.value) return
  if (autosaveTimer) clearTimeout(autosaveTimer)
  autosaveTimer = window.setTimeout(async () => {
    if (!document.value) return
    saving.value = true
    try {
      document.value = await window.mel.reports.save(document.value, false)
      await refresh()
    } finally {
      saving.value = false
    }
  }, 900)
}

watch(document, scheduleAutosave, { deep: true })

async function checkpoint() {
  if (!document.value) return
  saving.value = true
  try {
    document.value = await window.mel.reports.save(document.value, true)
    revisions.value = await window.mel.reports.revisions(document.value.id)
    await refresh()
    notify(`Checkpoint r${document.value.revision} saved.`)
  } finally {
    saving.value = false
  }
}

function addBlock(type: ReportBlock['type']) {
  if (!document.value) return
  const page = Math.max(1, ...document.value.blocks.map(block => block.layout.page))
  const block: ReportBlock = {
    id: uuid(),
    type,
    layout: defaultLayout(page),
    style: defaultStyle(),
    text: type === 'heading'
      ? 'New section'
      : type === 'rich-text'
        ? 'Write text here.'
        : type === 'callout'
          ? 'Important evidence note.'
          : undefined,
    caption: type === 'image' ? 'Image caption' : undefined,
    imageFit: 'contain',
    tone: 'info',
    statistics: type === 'statistics' ? [{ label: 'Metric', value: '0' }] : undefined,
  }
  if (type === 'heading') {
    block.style.fontSize = 30
    block.style.fontWeight = 700
  }
  document.value.blocks.push(block)
  selectedBlockId.value = block.id
}

function newPage() {
  if (!document.value) return
  const page = Math.max(1, ...document.value.blocks.map(block => block.layout.page)) + 1
  const block: ReportBlock = {
    id: uuid(),
    type: 'heading',
    layout: defaultLayout(page),
    style: { ...defaultStyle(), fontSize: 34, fontWeight: 800 },
    text: `Page ${page}`,
  }
  document.value.blocks.push(block)
  selectedBlockId.value = block.id
}

function updateBlock(block: ReportBlock) {
  if (!document.value) return
  const index = document.value.blocks.findIndex(item => item.id === block.id)
  if (index >= 0) document.value.blocks[index] = block
}

function moveBlock(id: string, direction: -1 | 1) {
  if (!document.value) return
  const index = document.value.blocks.findIndex(item => item.id === id)
  const target = index + direction
  if (index < 0 || target < 0 || target >= document.value.blocks.length) return
  ;[document.value.blocks[index], document.value.blocks[target]] = [document.value.blocks[target], document.value.blocks[index]]
}

function removeBlock(id: string) {
  if (!document.value) return
  document.value.blocks = document.value.blocks.filter(block => block.id !== id)
  selectedBlockId.value = document.value.blocks[0]?.id ?? ''
}

async function chooseImage(id: string) {
  const path = await window.mel.chooseFile({ title: 'Choose report image', extensions: ['jpg', 'jpeg', 'png', 'webp'] })
  if (!path || !document.value) return
  const block = document.value.blocks.find(item => item.id === id)
  if (block) block.imagePath = path
}

async function exportPdf() {
  if (!document.value) return
  const directory = await window.mel.chooseDirectory()
  if (!directory) return
  try {
    await checkpoint()
    const result = await window.mel.reports.exportPdf(document.value.id, directory)
    notify(`PDF exported: ${result.pdfPath}${result.warnings.length ? ` · ${result.warnings.length} warning(s)` : ''}`)
  } catch (error) {
    notify(error instanceof Error ? error.message : String(error))
  }
}

async function restore(revision: ReportRevisionSummary) {
  if (!document.value) return
  document.value = await window.mel.reports.restore(document.value.id, revision.path)
  revisions.value = await window.mel.reports.revisions(document.value.id)
  notify(`Restored revision ${revision.revision} as a new checkpoint.`)
}

async function removeDocument() {
  if (!document.value) return
  await window.mel.reports.delete(document.value.id)
  document.value = undefined
  appliedTemplate.value = null
  await refresh()
}

function previewStyle(block: ReportBlock) {
  const common = {
    fontFamily: block.style.fontFamily === 'serif' ? 'Georgia,serif' : block.style.fontFamily === 'mono' ? 'monospace' : 'system-ui,sans-serif',
    fontSize: `${Math.min(block.style.fontSize, 40)}px`,
    fontWeight: block.style.fontWeight,
    fontStyle: block.style.italic ? 'italic' : 'normal',
    textDecoration: block.style.underline ? 'underline' : 'none',
    textAlign: block.style.alignment,
    color: block.style.color,
    lineHeight: block.style.lineHeight,
  }
  return block.layout.mode === 'freeform'
    ? {
        ...common,
        position: 'absolute' as const,
        left: `${block.layout.x}%`,
        top: `${block.layout.y}%`,
        width: `${block.layout.width}%`,
        minHeight: `${block.layout.height}%`,
      }
    : { ...common, gridColumn: `span ${block.layout.span}` }
}

function templateApplied(snapshot: AppliedReportTemplate) {
  appliedTemplate.value = snapshot
  notify(`Applied immutable template snapshot “${snapshot.definition.name}”.`)
}

onMounted(async () => {
  await refresh()
  if (summaries.value[0]) await load(summaries.value[0].id)
})
onBeforeUnmount(() => autosaveTimer && clearTimeout(autosaveTimer))
</script>

<template>
  <div class="page-wrap">
    <PageHeader
      eyebrow="Report Library & Document Studio"
      title="Turn immutable evidence into a polished document"
      subtitle="Analysis snapshots remain unchanged while structured and controlled-freeform blocks, templates, revisions and PDF exports evolve independently."
      icon="mdi-file-chart-outline"
    >
      <div class="d-flex flex-wrap ga-2 mt-5">
        <v-btn color="primary" prepend-icon="mdi-file-plus-outline" @click="create">New report</v-btn>
        <v-btn color="secondary" variant="tonal" prepend-icon="mdi-image-import-outline" @click="importAtlas">Import Atlas manifest</v-btn>
        <v-btn v-if="document" color="success" variant="tonal" prepend-icon="mdi-file-pdf-box" @click="exportPdf">Export PDF</v-btn>
      </div>
    </PageHeader>

    <v-row>
      <v-col cols="12" lg="3">
        <v-card class="glass pa-3">
          <v-list nav>
            <v-list-item
              v-for="summary in summaries"
              :key="summary.id"
              :active="document?.id === summary.id"
              color="primary"
              rounded="lg"
              prepend-icon="mdi-file-document-outline"
              :title="summary.title"
              :subtitle="`${summary.template} · r${summary.revision} · ${summary.blockCount} blocks`"
              @click="load(summary.id)"
            />
          </v-list>
          <v-alert v-if="!summaries.length" color="info" variant="tonal" density="compact">No report documents yet.</v-alert>
        </v-card>
      </v-col>

      <v-col cols="12" lg="9">
        <v-card v-if="document" class="glass pa-5">
          <div class="d-flex flex-wrap align-center justify-space-between ga-3">
            <div>
              <div class="text-caption text-medium-emphasis">revision {{ document.revision }} · {{ saving ? 'autosaving…' : 'saved' }}</div>
              <div class="text-h5 font-weight-bold">{{ document.title }}</div>
            </div>
            <div class="d-flex ga-2">
              <v-btn variant="tonal" prepend-icon="mdi-content-save-check-outline" :loading="saving" @click="checkpoint">Checkpoint</v-btn>
              <v-btn color="error" variant="text" prepend-icon="mdi-delete-outline" @click="removeDocument">Delete</v-btn>
            </div>
          </div>

          <v-tabs v-model="tab" color="primary" class="mt-5">
            <v-tab value="editor">Editor</v-tab>
            <v-tab value="preview">Paged preview</v-tab>
            <v-tab value="templates">Templates</v-tab>
            <v-tab value="revisions">Revisions</v-tab>
          </v-tabs>

          <v-window v-model="tab" class="mt-5">
            <v-window-item value="editor">
              <v-row>
                <v-col cols="12" md="7">
                  <v-text-field v-model="document.title" label="Document title" prepend-inner-icon="mdi-format-title" />
                  <v-textarea v-model="document.subtitle" label="Subtitle / summary" rows="2" />
                  <v-select
                    v-model="document.template"
                    label="Built-in base template"
                    :items="REPORT_TEMPLATES.map(template => ({ title: template.title, value: template.id, props: { subtitle: template.description } }))"
                    prepend-inner-icon="mdi-palette-outline"
                  />
                  <div class="d-flex flex-wrap ga-2 mb-4">
                    <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-format-header-pound" @click="addBlock('heading')">Heading</v-btn>
                    <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-text-box-plus-outline" @click="addBlock('rich-text')">Text</v-btn>
                    <v-btn size="small" color="secondary" variant="tonal" prepend-icon="mdi-image-plus-outline" @click="addBlock('image')">Image</v-btn>
                    <v-btn size="small" color="accent" variant="tonal" prepend-icon="mdi-information-outline" @click="addBlock('callout')">Callout</v-btn>
                    <v-btn size="small" variant="tonal" prepend-icon="mdi-chart-box-plus-outline" @click="addBlock('statistics')">Statistics</v-btn>
                    <v-btn size="small" variant="tonal" prepend-icon="mdi-file-plus-outline" @click="newPage">New page</v-btn>
                  </div>
                  <v-slide-y-transition group>
                    <div v-for="(block, index) in document.blocks" :key="block.id" class="mb-3">
                      <ReportBlockEditor
                        :block="block"
                        :index="index"
                        :total="document.blocks.length"
                        :selected="selectedBlockId === block.id"
                        @select="selectedBlockId = $event"
                        @update="updateBlock"
                        @move="moveBlock"
                        @remove="removeBlock"
                        @choose-image="chooseImage"
                      />
                    </div>
                  </v-slide-y-transition>
                </v-col>
                <v-col cols="12" md="5">
                  <v-card variant="outlined" class="pa-5 position-sticky" style="top:16px">
                    <div class="text-overline text-primary">Document inspector</div>
                    <div class="text-h6 font-weight-bold">{{ currentTemplate.name }}</div>
                    <p class="text-body-2 text-medium-emphasis">{{ currentTemplate.description }}</p>
                    <v-chip v-if="appliedTemplate" color="success" variant="tonal" size="small">Immutable custom snapshot</v-chip>
                    <v-divider class="my-4" />
                    <template v-if="selectedBlock">
                      <div class="text-caption">Selected block</div>
                      <div class="font-weight-bold">{{ selectedBlock.type }} · page {{ selectedBlock.layout.page }}</div>
                      <div class="text-caption text-medium-emphasis mt-2">
                        {{ selectedBlock.layout.mode }} · {{ selectedBlock.style.fontFamily }} · {{ selectedBlock.style.fontSize }} px
                      </div>
                    </template>
                    <v-alert v-else color="info" variant="tonal" density="compact">Select a block to edit its style and layout.</v-alert>
                  </v-card>
                </v-col>
              </v-row>
            </v-window-item>

            <v-window-item value="preview">
              <div class="d-flex flex-column ga-6 align-center">
                <section
                  v-for="page in pages"
                  :key="page"
                  class="report-preview-page"
                  :style="{
                    background: currentTemplate.colors.background,
                    color: currentTemplate.colors.text,
                    aspectRatio: `${currentTemplate.page.widthInches}/${currentTemplate.page.heightInches}`,
                  }"
                >
                  <div
                    v-for="block in document.blocks.filter(item => item.layout.page === page)"
                    :key="block.id"
                    class="report-preview-block"
                    :style="previewStyle(block)"
                  >
                    <template v-if="block.type === 'image' || block.type === 'atlas-page'">
                      <div class="preview-image-placeholder">
                        <v-icon icon="mdi-image-outline" size="40" />
                        <span>{{ block.caption || block.imagePath || 'Image' }}</span>
                      </div>
                    </template>
                    <template v-else-if="block.type === 'statistics'">
                      <div class="d-flex flex-wrap ga-3">
                        <div v-for="item in block.statistics" :key="item.label">
                          <strong>{{ item.value }}</strong>
                          <div class="text-caption">{{ item.label }}</div>
                        </div>
                      </div>
                    </template>
                    <template v-else>{{ block.text }}</template>
                  </div>
                  <div class="preview-page-number">{{ page }}</div>
                </section>
              </div>
            </v-window-item>

            <v-window-item value="templates">
              <ReportTemplateLibrary :document-id="document.id" @applied="templateApplied" />
            </v-window-item>

            <v-window-item value="revisions">
              <v-list v-if="revisions.length">
                <v-list-item
                  v-for="revision in revisions"
                  :key="revision.path"
                  prepend-icon="mdi-history"
                  :title="`Revision ${revision.revision}`"
                  :subtitle="revision.createdAt"
                >
                  <template #append>
                    <v-btn size="small" variant="tonal" prepend-icon="mdi-backup-restore" @click="restore(revision)">Restore</v-btn>
                  </template>
                </v-list-item>
              </v-list>
              <v-alert v-else color="info" variant="tonal">Create a checkpoint to preserve an explicit revision snapshot.</v-alert>
            </v-window-item>
          </v-window>
        </v-card>

        <v-card v-else class="glass pa-10 text-center">
          <v-icon icon="mdi-file-document-plus-outline" color="primary" size="72" />
          <div class="text-h5 font-weight-bold mt-4">Create or import a report</div>
        </v-card>
      </v-col>
    </v-row>
    <v-snackbar v-model="snackbar" :timeout="7000">{{ message }}</v-snackbar>
  </div>
</template>

<style scoped>
.report-preview-page {
  width: min(100%, 900px);
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-rows: min-content;
  gap: 14px;
  padding: 4%;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
  border-radius: 6px;
}
.report-preview-block { white-space: pre-wrap; overflow: hidden; }
.preview-image-placeholder {
  min-height: 140px;
  border: 1px dashed currentColor;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  opacity: 0.65;
}
.preview-page-number { position: absolute; right: 18px; bottom: 12px; font-size: 11px; opacity: 0.5; }
.position-sticky { position: sticky; }
</style>
