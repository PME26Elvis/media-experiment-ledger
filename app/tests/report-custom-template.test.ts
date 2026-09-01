import { describe, expect, it } from 'vitest'
import { renderReportHtml } from '../src/main/report-renderer'
import type { ReportDocument } from '../src/shared/contracts'
import type { ReportTemplateDefinition } from '../src/shared/template-contracts'

const document: ReportDocument = {
  schemaVersion: 1,
  id: '11111111-1111-4111-8111-111111111111',
  title: 'Snapshot report',
  subtitle: 'Evidence',
  template: 'research-light',
  revision: 1,
  createdAt: '2026-07-23T00:00:00.000Z',
  updatedAt: '2026-07-23T00:00:00.000Z',
  blocks: [{
    id: '22222222-2222-4222-8222-222222222222',
    type: 'heading',
    layout: { mode: 'structured', span: 2, page: 1, x: 0, y: 0, width: 100, height: 10 },
    style: {
      fontFamily: 'sans', fontSize: 32, fontWeight: 700, italic: false,
      underline: false, alignment: 'left', color: '#101010', lineHeight: 1.4,
    },
    text: 'Immutable template evidence',
  }],
}

const custom: ReportTemplateDefinition = {
  schemaVersion: 1,
  name: 'Laboratory Copper',
  description: 'Custom immutable snapshot',
  page: { widthInches: 11, heightInches: 8.5 },
  marginInches: 0.62,
  colors: {
    background: '#120f0d',
    surface: '#241c17',
    text: '#fff7ed',
    muted: '#d6bfae',
    primary: '#c26d3a',
    accent: '#5aa89b',
  },
  fontFamily: 'Georgia, serif',
}

describe('custom report template rendering', () => {
  it('uses an immutable custom definition instead of the built-in base template', () => {
    const rendered = renderReportHtml(document, custom)
    expect(rendered.html).toContain('@page{size:11in 8.5in')
    expect(rendered.html).toContain('padding:0.62in')
    expect(rendered.html).toContain('background:#120f0d')
    expect(rendered.html).toContain('font-family:Georgia, serif')
    expect(rendered.html).not.toContain('background:#ffffff')
  })
})
