'use strict'

const { app, BrowserWindow } = require('electron')
const { createHash } = require('node:crypto')
const { mkdtempSync, rmSync, writeFileSync } = require('node:fs')
const { tmpdir } = require('node:os')
const { join, resolve } = require('node:path')
const { pathToFileURL } = require('node:url')
const { performance } = require('node:perf_hooks')

const APP_ROOT = resolve(__dirname, '..')
const OUTPUT_PATH = resolve(process.env.MEL_REPORT_BENCHMARK_OUTPUT || join(APP_ROOT, 'report-500-page-benchmark.json'))
const PDF_PATH = resolve(process.env.MEL_REPORT_BENCHMARK_PDF || join(APP_ROOT, 'report-500-page-benchmark.pdf'))
const PAGE_COUNT = Number(process.env.MEL_REPORT_BENCHMARK_PAGES || 500)
const MAX_RENDER_MS = 5000
const MAX_PRINT_MS = 150000
const MAX_RSS_DELTA_BYTES = 768 * 1024 * 1024
const MAX_PDF_BYTES = 250 * 1024 * 1024

function reportBlock(page, index, type, text, size = 14) {
  return {
    id: `page-${page}-block-${index}`,
    type,
    layout: { mode: 'structured', span: type === 'heading' ? 2 : 1, page, x: 0, y: 0, width: 100, height: 20 },
    style: { fontFamily: 'sans', fontSize: size, fontWeight: type === 'heading' ? 700 : 400, italic: false, underline: false, alignment: 'left', color: '#172033', lineHeight: 1.4 },
    text,
    statistics: type === 'statistics'
      ? [
          { label: 'Page', value: String(page) },
          { label: 'Evidence rows', value: String(page * 17) },
          { label: 'Hash group', value: createHash('sha256').update(String(page)).digest('hex').slice(0, 8) },
        ]
      : undefined,
  }
}

function buildDocument() {
  const blocks = []
  for (let page = 1; page <= PAGE_COUNT; page += 1) {
    blocks.push(reportBlock(page, 1, 'heading', `Stable qualification evidence — page ${page}`, 28))
    blocks.push(reportBlock(page, 2, 'rich-text', `Deterministic local report content for page ${page}. This paragraph exercises escaping, typography, structured grid layout and page boundaries without external media.`))
    blocks.push(reportBlock(page, 3, 'statistics', ''))
  }
  return {
    schemaVersion: 1,
    id: 'stable-500-page-benchmark',
    title: 'Media Experiment Ledger Studio — 500-page qualification',
    subtitle: 'Deterministic Chromium PDF export benchmark',
    template: 'research-light',
    blocks,
    revision: 1,
    createdAt: '2026-01-01T00:00:00.000Z',
    updatedAt: '2026-01-01T00:00:00.000Z',
  }
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex')
}

function writeFailureEvidence(error) {
  const evidence = {
    schema_version: 1,
    page_target: PAGE_COUNT,
    passed: false,
    error: {
      name: error instanceof Error ? error.name : 'Error',
      message: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    },
    output_pdf: PDF_PATH,
    created_at: new Date().toISOString(),
  }
  writeFileSync(OUTPUT_PATH, `${JSON.stringify(evidence, null, 2)}\n`, 'utf8')
  return evidence
}

async function main() {
  const root = mkdtempSync(join(tmpdir(), 'mel-report-benchmark-'))
  const initialRss = process.memoryUsage().rss
  let window
  try {
    const { renderReportHtml } = require(join(APP_ROOT, 'dist', 'main', 'main', 'report-renderer.js'))
    const document = buildDocument()
    const renderStarted = performance.now()
    const first = renderReportHtml(document)
    const renderMs = performance.now() - renderStarted
    const second = renderReportHtml(document)
    const firstHash = sha256(Buffer.from(first.html, 'utf8'))
    const secondHash = sha256(Buffer.from(second.html, 'utf8'))
    const htmlPageCount = (first.html.match(/<section class="page(?: freeform)?">/g) || []).length
    const htmlPath = join(root, 'report.html')
    writeFileSync(htmlPath, first.html, 'utf8')

    window = new BrowserWindow({
      show: false,
      webPreferences: {
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
        webSecurity: true,
      },
    })
    await window.loadURL(pathToFileURL(htmlPath).href)
    const printStarted = performance.now()
    const pdf = await window.webContents.printToPDF({
      printBackground: true,
      preferCSSPageSize: true,
      generateTaggedPDF: true,
      generateDocumentOutline: true,
    })
    const printMs = performance.now() - printStarted
    writeFileSync(PDF_PATH, pdf)
    const rssDeltaBytes = Math.max(0, process.memoryUsage().rss - initialRss)
    const evidence = {
      schema_version: 1,
      page_target: PAGE_COUNT,
      html_page_count: htmlPageCount,
      block_count: document.blocks.length,
      html_bytes: Buffer.byteLength(first.html, 'utf8'),
      pdf_bytes: pdf.byteLength,
      pdf_sha256: sha256(pdf),
      deterministic_html: firstHash === secondHash,
      html_sha256: firstHash,
      warnings: first.warnings,
      render_ms: Math.round(renderMs * 100) / 100,
      print_ms: Math.round(printMs * 100) / 100,
      rss_delta_bytes: rssDeltaBytes,
      thresholds: {
        max_render_ms: MAX_RENDER_MS,
        max_print_ms: MAX_PRINT_MS,
        max_rss_delta_bytes: MAX_RSS_DELTA_BYTES,
        max_pdf_bytes: MAX_PDF_BYTES,
      },
      criteria: {
        exact_html_pages: htmlPageCount === PAGE_COUNT,
        deterministic_html: firstHash === secondHash,
        no_render_warnings: first.warnings.length === 0,
        render_time: renderMs <= MAX_RENDER_MS,
        print_time: printMs <= MAX_PRINT_MS,
        memory: rssDeltaBytes <= MAX_RSS_DELTA_BYTES,
        pdf_size: pdf.byteLength > 4 && pdf.byteLength <= MAX_PDF_BYTES,
        pdf_header: pdf.subarray(0, 4).toString('ascii') === '%PDF',
      },
      output_pdf: PDF_PATH,
      created_at: new Date().toISOString(),
    }
    evidence.passed = Object.values(evidence.criteria).every(Boolean)
    writeFileSync(OUTPUT_PATH, `${JSON.stringify(evidence, null, 2)}\n`, 'utf8')
    console.log(JSON.stringify(evidence, null, 2))
    if (!evidence.passed) process.exitCode = 1
  } finally {
    if (window && !window.isDestroyed()) window.destroy()
    rmSync(root, { recursive: true, force: true })
  }
}

app.whenReady().then(main).catch(error => {
  const evidence = writeFailureEvidence(error)
  console.error(JSON.stringify(evidence, null, 2))
  process.exitCode = 1
}).finally(() => app.quit())
