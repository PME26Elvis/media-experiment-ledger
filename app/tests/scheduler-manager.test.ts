import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import type { JobRecord } from '../src/shared/contracts'
import { SchedulerManager } from '../src/main/scheduler-manager'

const roots: string[] = []
function temporaryRoot(): string {
  const root = mkdtempSync(join(tmpdir(), 'mel-scheduler-'))
  roots.push(root)
  return root
}
afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true })
})

function completedJob(): JobRecord {
  const now = new Date().toISOString()
  return {
    id: '11111111-1111-4111-8111-111111111111',
    kind: 'scan',
    title: 'Scheduled scan',
    status: 'queued',
    stage: 'queued',
    progress: 0,
    completedItems: 0,
    totalItems: 0,
    config: {},
    createdAt: now,
    updatedAt: now,
  }
}

describe('SchedulerManager', () => {
  it('writes and registers a systemd-user timer without shell interpolation', async () => {
    const root = temporaryRoot()
    const commands: string[][] = []
    const manager = new SchedulerManager(root, {
      platform: 'linux',
      homeDirectory: join(root, 'home'),
      executablePath: '/opt/Media Experiment Ledger Studio/studio',
      runCommand: async (command, args) => { commands.push([command, ...args]) },
      createJob: () => completedJob(),
    })
    const saved = await manager.save({
      name: 'Nightly scan',
      enabled: true,
      cadence: { kind: 'daily', hour: 2, minute: 30 },
      job: { kind: 'scan', title: 'Scheduled scan', config: { source: '/data' } },
    })
    expect(saved.backend).toBe('systemd-user')
    expect(commands).toEqual([
      ['systemctl', '--user', 'daemon-reload'],
      ['systemctl', '--user', 'enable', '--now', `media-experiment-ledger-studio-${saved.id}.timer`],
    ])
    const service = readFileSync(join(root, 'home', '.config', 'systemd', 'user', `media-experiment-ledger-studio-${saved.id}.service`), 'utf8')
    expect(service).toContain('ExecStart="/opt/Media Experiment Ledger Studio/studio"')
    expect(service).toContain(`"--mel-schedule=${saved.id}"`)
    expect(await manager.runNow(saved.id)).toMatchObject({ kind: 'scan', status: 'queued' })
    expect(await manager.remove(saved.id)).toBe(true)
  })

  it('generates a constrained Windows weekly task command', () => {
    const manager = new SchedulerManager(temporaryRoot(), {
      platform: 'win32',
      executablePath: 'C:\\Program Files\\MEL Studio\\studio.exe',
      createJob: () => completedJob(),
    })
    const preview = manager.preview({
      name: 'Weekly Atlas',
      enabled: true,
      cadence: { kind: 'weekly', weekdays: [1, 3, 5], hour: 8, minute: 5 },
      job: { kind: 'atlas', title: 'Weekly Atlas', config: {} },
    })
    expect(preview.backend).toBe('task-scheduler')
    expect(preview.files).toEqual([])
    expect(preview.commands[0]).toContain('MON,WED,FRI')
    expect(preview.commands[0]).toContain('08:05')
  })
})
