import { existsSync, statSync } from 'node:fs'
import { pathToFileURL } from 'node:url'
import type { ReportBlock, ReportDocument, ReportTextStyle } from '../shared/contracts'
import { reportTemplate } from '../shared/report-templates'

export interface RenderedReport { html: string; warnings: string[] }

export function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

function color(value: string, fallback: string): string {
  return /^#[0-9a-f]{6}$/iu.test(value) ? value : fallback
}

function textStyle(style: ReportTextStyle): string {
  const families = {
    sans: 'Inter,system-ui,sans-serif',
    serif: 'Georgia,Times New Roman,serif',
    mono: 'ui-monospace,SFMono-Regular,monospace',
  }
  return [
    `font-family:${families[style.fontFamily]}`,
    `font-size:${clamp(style.fontSize, 8, 96)}px`,
    `font-weight:${style.fontWeight}`,
    `font-style:${style.italic ? 'italic' : 'normal'}`,
    `text-decoration:${style.underline ? 'underline' : 'none'}`,
    `text-align:${style.alignment}`,
    `color:${color(style.color, '#172033')}`,
    `line-height:${clamp(style.lineHeight, 1, 2.5)}`,
  ].join(';')
}

function blockLayout(block: ReportBlock): string {
  if (block.layout.mode === 'freeform') {
    return [
      'position:absolute',
      `left:${clamp(block.layout.x, 0, 100)}%`,
      `top:${clamp(block.layout.y, 0, 100)}%`,
      `width:${clamp(block.layout.width, 5, 100)}%`,
      `min-height:${clamp(block.layout.height, 2, 100)}%`,
    ].join(';') + ';'
  }
  return `grid-column:span ${block.layout.span};`
}

function imageUrl(path: string | undefined, warnings: string[]): string | undefined {
  if (!path) {
    warnings.push('Missing image path.')
    return undefined
  }
  if (/\0|[\u0001-\u001f\u007f]/u.test(path)) {
    warnings.push(`Invalid image path: ${path.replaceAll('\0', '\\0')}`)
    return undefined
  }
  try {
    if (!existsSync(path)) {
      warnings.push(`Missing image: ${path}`)
      return undefined
    }
    if (!statSync(path).isFile()) {
      warnings.push(`Invalid image path: ${path}`)
      return undefined
    }
    return pathToFileURL(path).href
  } catch {
    warnings.push(`Invalid image path: ${path}`)
    return undefined
  }
}

function renderBlock(block: ReportBlock, warnings: string[]): string {
  const style = `${blockLayout(block)}${textStyle(block.style)}`
  const text = escapeHtml(block.text ?? '').replaceAll('\n', '<br>')

  if (block.type === 'heading') {
    const level = block.style.fontSize >= 34 ? 1 : block.style.fontSize >= 24 ? 2 : 3
    return `<h${level} class="block heading" style="${style}">${text}</h${level}>`
  }
  if (block.type === 'rich-text') return `<div class="block rich-text" style="${style}">${text}</div>`
  if (block.type === 'callout') return `<aside class="block callout ${block.tone ?? 'info'}" style="${style}">${text}</aside>`
  if (block.type === 'statistics') {
    const rows = (block.statistics ?? [])
      .map(row => `<div class="stat"><strong>${escapeHtml(row.value)}</strong><span>${escapeHtml(row.label)}</span></div>`)
      .join('')
    return `<div class="block statistics" style="${style}">${rows}</div>`
  }
  if (block.type === 'image' || block.type === 'atlas-page') {
    const url = imageUrl(block.imagePath, warnings)
    const media = url
      ? `<img src="${escapeHtml(url)}" alt="${escapeHtml(block.caption ?? 'Report image')}" style="object-fit:${block.imageFit ?? 'contain'}">`
      : '<div class="missing-image">Image unavailable</div>'
    return `<figure class="block image-block" style="${style}">${media}${block.caption ? `<figcaption>${escapeHtml(block.caption)}</figcaption>` : ''}</figure>`
  }
  return ''
}

export function renderReportHtml(document: ReportDocument): RenderedReport {
  const template = reportTemplate(document.template)
  const warnings: string[] = []
  const maxPage = Math.max(1, ...document.blocks.map(block => block.layout.page))
  const pages = Array.from({ length: maxPage }, (_, index) => index + 1)
    .map(page => {
      const blocks = document.blocks.filter(block => block.layout.page === page && block.type !== 'page-break')
      const freeform = blocks.some(block => block.layout.mode === 'freeform')
      return `<section class="page ${freeform ? 'freeform' : ''}">${blocks.map(block => renderBlock(block, warnings)).join('')}</section>`
    })
    .join('')

  const css = `@page{size:${template.page.widthInches}in ${template.page.heightInches}in;margin:0}*{box-sizing:border-box}html,body{margin:0;padding:0;background:${template.colors.background};color:${template.colors.text};font-family:${template.fontFamily};print-color-adjust:exact;-webkit-print-color-adjust:exact}.page{width:${template.page.widthInches}in;height:${template.page.heightInches}in;padding:${template.marginInches}in;background:${template.colors.background};display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-auto-rows:min-content;gap:18px;overflow:hidden;break-after:page;position:relative}.page.freeform{display:block}.block{margin:0;overflow-wrap:anywhere}.heading{letter-spacing:-.03em}.rich-text{white-space:normal}.callout{padding:18px;border-radius:14px;background:${template.colors.surface};border-left:5px solid ${template.colors.primary}}.callout.success{border-color:#22c55e}.callout.warning{border-color:#f59e0b}.callout.error{border-color:#ef4444}.image-block{display:flex;flex-direction:column;gap:8px;min-height:120px}.image-block img{width:100%;height:100%;max-height:8.8in;border-radius:12px;background:${template.colors.surface}}figcaption{font-size:11px;color:${template.colors.muted}}.missing-image{height:180px;display:grid;place-items:center;background:${template.colors.surface};color:${template.colors.muted};border:1px dashed ${template.colors.muted};border-radius:12px}.statistics{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px}.stat{padding:16px;background:${template.colors.surface};border-radius:12px}.stat strong{display:block;font-size:26px;color:${template.colors.primary}}.stat span{font-size:11px;color:${template.colors.muted}}`
  const html = `<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src file: data:; style-src 'unsafe-inline';"><title>${escapeHtml(document.title)}</title><style>${css}</style></head><body>${pages}</body></html>`
  return { html, warnings }
}
