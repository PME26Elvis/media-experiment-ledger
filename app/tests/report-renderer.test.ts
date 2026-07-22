import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { afterEach, describe, expect, it } from 'vitest'
import type { ReportBlock, ReportDocument } from '../src/shared/contracts'
import { escapeHtml, renderReportHtml } from '../src/main/report-renderer'
import { reportTemplate } from '../src/shared/report-templates'

const temporaryDirectories: string[] = []
afterEach(() => {
  for (const directory of temporaryDirectories.splice(0)) {
    rmSync(directory, { recursive: true, force: true })
  }
})

const baseStyle: ReportBlock['style'] = {
  fontFamily: 'sans',
  fontSize: 18,
  fontWeight: 400,
  italic: false,
  underline: false,
  alignment: 'left',
  color: '#172033',
  lineHeight: 1.5,
}

function block(
  id: string,
  type: ReportBlock['type'],
  patch: Partial<ReportBlock> = {},
): ReportBlock {
  return {
    id,
    type,
    layout: {
      mode: 'structured',
      span: 2,
      page: 1,
      x: 0,
      y: 0,
      width: 100,
      height: 10,
    },
    style: { ...baseStyle },
    ...patch,
  }
}

function report(blocks: ReportBlock[]): ReportDocument {
  return {
    schemaVersion: 1,
    id: '11111111-1111-4111-8111-111111111111',
    title: '<script>alert(1)</script>',
    subtitle: 'Evidence',
    template: 'research-light',
    revision: 1,
    createdAt: '2026-07-22T00:00:00.000Z',
    updatedAt: '2026-07-22T00:00:00.000Z',
    blocks,
  }
}

describe('report renderer', () => {
  it('escapes user-authored markup and uses a restrictive CSP', () => {
    const rendered = renderReportHtml(report([
      block('22222222-2222-4222-8222-222222222222', 'rich-text', {
        text: '<img src=x onerror=alert(1)>\nSafe line',
      }),
    ]))
    expect(rendered.html).toContain("default-src 'none'")
    expect(rendered.html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;')
    expect(rendered.html).not.toContain('<img src=x onerror=alert(1)>')
    expect(rendered.html).toContain('&lt;img src=x onerror=alert(1)&gt;')
  })

  it('renders heading levels, callouts, statistics and freeform layout', () => {
    const rendered = renderReportHtml(report([
      block('22222222-2222-4222-8222-222222222221', 'heading', {
        text: 'Primary',
        style: { ...baseStyle, fontSize: 42, fontWeight: 800 },
      }),
      block('22222222-2222-4222-8222-222222222222', 'heading', {
        text: 'Secondary',
        style: { ...baseStyle, fontSize: 28, fontWeight: 700 },
      }),
      block('22222222-2222-4222-8222-222222222223', 'heading', {
        text: 'Tertiary',
        style: { ...baseStyle, fontSize: 18, fontWeight: 600 },
      }),
      block('22222222-2222-4222-8222-222222222224', 'callout', {
        text: 'Warning evidence',
        tone: 'warning',
        layout: {
          mode: 'freeform',
          span: 1,
          page: 2,
          x: -10,
          y: 110,
          width: 150,
          height: 1,
        },
        style: {
          ...baseStyle,
          fontSize: 120,
          lineHeight: 4,
          color: 'invalid',
        },
      }),
      block('22222222-2222-4222-8222-222222222225', 'statistics', {
        statistics: [
          { label: 'Images', value: '387' },
          { label: 'Boxes', value: '3243' },
        ],
      }),
      block('22222222-2222-4222-8222-222222222226', 'page-break'),
    ]))
    expect(rendered.html).toContain('<h1')
    expect(rendered.html).toContain('<h2')
    expect(rendered.html).toContain('<h3')
    expect(rendered.html).toContain('callout warning')
    expect(rendered.html).toContain('page freeform')
    expect(rendered.html).toContain('<strong>387</strong>')
    expect(rendered.html).toContain('left:0%')
    expect(rendered.html).toContain('top:100%')
    expect(rendered.html).toContain('font-size:96px')
    expect(rendered.html).toContain('line-height:2.5')
  })

  it('renders verified local images and reports missing or invalid paths', () => {
    const directory = mkdtempSync(join(tmpdir(), 'mel-report-renderer-'))
    temporaryDirectories.push(directory)
    const existing = join(directory, 'image.png')
    writeFileSync(existing, 'not-decoded-by-preflight')
    const rendered = renderReportHtml(report([
      block('33333333-3333-4333-8333-333333333331', 'image', {
        imagePath: existing,
        caption: 'Existing',
        imageFit: 'cover',
      }),
      block('33333333-3333-4333-8333-333333333332', 'atlas-page', {
        imagePath: join(directory, 'missing.png'),
        caption: 'Missing',
      }),
      block('33333333-3333-4333-8333-333333333333', 'image', {
        imagePath: '\0invalid',
        caption: 'Invalid',
      }),
      block('33333333-3333-4333-8333-333333333334', 'image', {
        caption: 'No path',
      }),
    ]))
    expect(rendered.html).toContain(pathToFileURL(existing).href)
    expect(rendered.html).toContain('object-fit:cover')
    expect(rendered.html.match(/Image unavailable/g)?.length).toBe(3)
    expect(rendered.warnings).toHaveLength(3)
    expect(rendered.warnings.some((warning) => warning.includes('Missing image'))).toBe(true)
    expect(rendered.warnings.some((warning) => warning.includes('Invalid image'))).toBe(true)
  })

  it('resolves all templates and rejects unknown template IDs', () => {
    expect(reportTemplate('traditional-chinese-academic').title).toContain('Traditional')
    expect(reportTemplate('presentation-16-9').page.widthInches).toBeGreaterThan(10)
    expect(() => reportTemplate('unknown' as never)).toThrow(/Unknown report template/u)
  })

  it('escapes all HTML-significant characters', () => {
    expect(escapeHtml(`<&>"'`)).toBe('&lt;&amp;&gt;&quot;&#39;')
  })
})
