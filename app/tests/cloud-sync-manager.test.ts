import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import { CloudSyncManager } from '../src/main/cloud-sync-manager'

const roots: string[] = []
function root(name: string): string {
  const value = mkdtempSync(join(tmpdir(), `mel-sync-${name}-`))
  roots.push(value)
  return value
}
afterEach(() => {
  for (const value of roots.splice(0)) rmSync(value, { recursive: true, force: true })
})

describe('CloudSyncManager', () => {
  it('preserves local edits and writes the remote side of a two-device conflict', () => {
    const projectA = root('a')
    const projectB = root('b')
    const remote = root('remote')
    const sync = new CloudSyncManager()

    writeFileSync(join(projectA, 'notes.txt'), 'base')
    expect(sync.sync({ projectRoot: projectA, syncRoot: remote }).direction).toBe('initialized')
    expect(sync.sync({ projectRoot: projectB, syncRoot: remote }).direction).toBe('downloaded')
    expect(readFileSync(join(projectB, 'notes.txt'), 'utf8')).toBe('base')

    writeFileSync(join(projectA, 'notes.txt'), 'device-a')
    writeFileSync(join(projectB, 'notes.txt'), 'device-b')
    expect(sync.sync({ projectRoot: projectA, syncRoot: remote }).direction).toBe('uploaded')
    const merged = sync.sync({ projectRoot: projectB, syncRoot: remote })

    expect(merged.direction).toBe('merged')
    expect(merged.conflicts).toHaveLength(1)
    expect(merged.conflicts[0]?.path).toBe('notes.txt')
    expect(readFileSync(join(projectB, 'notes.txt'), 'utf8')).toBe('device-b')
    expect(readFileSync(merged.conflicts[0]!.remoteCopyPath!, 'utf8')).toBe('device-a')

    const reconciled = sync.sync({ projectRoot: projectA, syncRoot: remote })
    expect(reconciled.direction).toBe('downloaded')
    expect(readFileSync(join(projectA, 'notes.txt'), 'utf8')).toBe('device-b')
  })

  it('rejects nested project and sync roots', () => {
    const project = root('nested')
    const sync = new CloudSyncManager()
    expect(() => sync.sync({ projectRoot: project, syncRoot: join(project, 'remote') }))
      .toThrow(/separate, non-nested/u)
  })
})
