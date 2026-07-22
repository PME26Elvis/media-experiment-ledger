import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import { TemplateManager } from '../src/main/template-manager'

const roots: string[] = []
function root(): string {
  const path = mkdtempSync(join(tmpdir(), 'mel-template-test-'))
  roots.push(path)
  return path
}
function validTemplate() {
  return {
    schemaVersion: 1,
    name: 'Lab Review',
    description: 'A restrained laboratory template.',
    page: { widthInches: 8.5, heightInches: 11 },
    marginInches: 0.5,
    colors: {
      background: '#f7f8fc', surface: '#ffffff', text: '#172033', muted: '#5d6783', primary: '#4056d6', accent: '#00a6a6',
    },
    fontFamily: 'Inter, system-ui, sans-serif',
  }
}
afterEach(() => {
  for (const path of roots.splice(0)) rmSync(path, { recursive: true, force: true })
})

describe('TemplateManager', () => {
  it('imports, exports and applies a document-scoped immutable snapshot', () => {
    const userData = root()
    const source = join(userData, 'source.json')
    writeFileSync(source, JSON.stringify(validTemplate()), 'utf8')
    const documents = join(userData, 'reports', 'documents')
    mkdirSync(documents, { recursive: true })
    const documentId = '11111111-1111-4111-8111-111111111111'
    writeFileSync(join(documents, `${documentId}.json`), '{}', 'utf8')
    const manager = new TemplateManager(userData)
    const imported = manager.import(source)
    expect(manager.list()).toHaveLength(1)
    const applied = manager.apply(documentId, imported.id)
    expect(applied.definition.name).toBe('Lab Review')
    expect(manager.templateForDocument(documentId)?.colors.primary).toBe('#4056d6')
    const exportRoot = join(userData, 'export')
    const exported = manager.export(imported.id, exportRoot)
    expect(JSON.parse(readFileSync(exported, 'utf8'))).toEqual(validTemplate())
    expect(manager.remove(imported.id)).toBe(true)
    expect(manager.list()).toHaveLength(0)
    expect(manager.templateForDocument(documentId)?.name).toBe('Lab Review')
  })

  it('rejects executable-looking fonts, invalid colors and unsafe page dimensions', () => {
    const userData = root()
    const manager = new TemplateManager(userData)
    for (const patch of [
      { colors: { ...validTemplate().colors, primary: 'url(javascript:alert(1))' } },
      { fontFamily: 'Inter; background:url(file:///secret)' },
      { page: { widthInches: 100, heightInches: 11 } },
    ]) {
      const source = join(userData, `invalid-${Math.random()}.json`)
      writeFileSync(source, JSON.stringify({ ...validTemplate(), ...patch }), 'utf8')
      expect(() => manager.import(source)).toThrow()
    }
  })

  it('rejects applying a template to a missing document', () => {
    const userData = root()
    const source = join(userData, 'source.json')
    writeFileSync(source, JSON.stringify(validTemplate()), 'utf8')
    const manager = new TemplateManager(userData)
    const imported = manager.import(source)
    expect(() => manager.apply('22222222-2222-4222-8222-222222222222', imported.id)).toThrow(/does not exist/u)
  })
})
