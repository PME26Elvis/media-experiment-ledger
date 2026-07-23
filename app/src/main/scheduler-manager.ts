import { execFile } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'
import { mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs'
import type {
  SaveScheduleRequest,
  ScheduledJobDefinition,
  SchedulerPreview,
} from '../shared/integration-contracts'
import type { JobRecord } from '../shared/contracts'

interface SchedulerRegistry {
  schemaVersion: 1
  schedules: ScheduledJobDefinition[]
}

type CommandRunner = (command: string, args: string[]) => Promise<void>
type JobCreator = (request: SaveScheduleRequest['job']) => Promise<JobRecord> | JobRecord

export interface SchedulerManagerOptions {
  platform?: NodeJS.Platform
  homeDirectory?: string
  executablePath?: string
  uid?: number
  runCommand?: CommandRunner
  createJob: JobCreator
}

function defaultCommandRunner(command: string, args: string[]): Promise<void> {
  return new Promise((resolve, reject) => {
    execFile(command, args, { windowsHide: true, timeout: 30_000 }, (error, _stdout, stderr) => {
      if (error) {
        reject(new Error(`${command} failed: ${String(stderr || error.message).trim()}`))
        return
      }
      resolve()
    })
  })
}

function atomicJson(path: string, value: unknown): void {
  mkdirSync(dirname(path), { recursive: true })
  const temporary = `${path}.tmp`
  writeFileSync(temporary, JSON.stringify(value, null, 2) + '\n', { encoding: 'utf8', mode: 0o600 })
  renameSync(temporary, path)
}

function atomicText(path: string, content: string): void {
  mkdirSync(dirname(path), { recursive: true })
  const temporary = `${path}.tmp`
  writeFileSync(temporary, content, { encoding: 'utf8', mode: 0o600 })
  renameSync(temporary, path)
}

function xml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;')
}

function systemdQuote(value: string): string {
  return `"${value.replaceAll('\\', '\\\\').replaceAll('"', '\\"')}"`
}

function clock(hour: number, minute: number): string {
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`
}

function weekdayNames(days: number[]): string[] {
  const names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  return [...new Set(days)].sort((a, b) => a - b).map(day => names[day]!)
}

function normalizeRequest(request: SaveScheduleRequest): SaveScheduleRequest {
  return {
    ...request,
    name: request.name.trim(),
    job: {
      ...request.job,
      title: request.job.title.trim(),
      config: structuredClone(request.job.config),
    },
    cadence: structuredClone(request.cadence),
  }
}

export class SchedulerManager {
  private readonly platform: NodeJS.Platform
  private readonly homeDirectory: string
  private readonly executablePath: string
  private readonly uid: number
  private readonly runCommand: CommandRunner
  private readonly createJob: JobCreator
  private readonly registryPath: string

  constructor(userDataPath: string, options: SchedulerManagerOptions) {
    this.platform = options.platform ?? process.platform
    this.homeDirectory = options.homeDirectory ?? homedir()
    this.executablePath = options.executablePath ?? process.execPath
    this.uid = options.uid ?? process.getuid?.() ?? 0
    this.runCommand = options.runCommand ?? defaultCommandRunner
    this.createJob = options.createJob
    this.registryPath = join(userDataPath, 'integrations', 'schedules.json')
  }

  list(): ScheduledJobDefinition[] {
    return this.readRegistry().schedules.sort((a, b) => a.name.localeCompare(b.name))
  }

  preview(request: SaveScheduleRequest): SchedulerPreview {
    const normalized = normalizeRequest(request)
    const id = normalized.id ?? 'preview'
    if (this.platform === 'win32') return this.windowsPreview(id, normalized)
    if (this.platform === 'darwin') return this.macPreview(id, normalized)
    if (this.platform === 'linux') return this.linuxPreview(id, normalized)
    throw new Error(`OS scheduling is not supported on ${this.platform}.`)
  }

  async save(request: SaveScheduleRequest): Promise<ScheduledJobDefinition> {
    const normalized = normalizeRequest(request)
    const registry = this.readRegistry()
    const existing = normalized.id ? registry.schedules.find(item => item.id === normalized.id) : undefined
    const now = new Date().toISOString()
    const id = existing?.id ?? normalized.id ?? randomUUID()
    const preview = this.preview({ ...normalized, id })
    const record: ScheduledJobDefinition = {
      ...normalized,
      id,
      backend: preview.backend,
      createdAt: existing?.createdAt ?? now,
      updatedAt: now,
    }

    if (existing) await this.uninstall(existing)
    if (record.enabled) await this.installPreview(preview)

    const schedules = registry.schedules.filter(item => item.id !== id)
    schedules.push(record)
    atomicJson(this.registryPath, { schemaVersion: 1, schedules } satisfies SchedulerRegistry)
    return record
  }

  async remove(id: string): Promise<boolean> {
    const registry = this.readRegistry()
    const existing = registry.schedules.find(item => item.id === id)
    if (!existing) return false
    await this.uninstall(existing)
    atomicJson(this.registryPath, {
      schemaVersion: 1,
      schedules: registry.schedules.filter(item => item.id !== id),
    } satisfies SchedulerRegistry)
    return true
  }

  async runNow(id: string): Promise<JobRecord> {
    const schedule = this.readRegistry().schedules.find(item => item.id === id)
    if (!schedule) throw new Error('Scheduled job was not found.')
    return await this.createJob(structuredClone(schedule.job))
  }

  private async installPreview(preview: SchedulerPreview): Promise<void> {
    for (const file of preview.files) atomicText(file.path, file.content)
    for (const [command, ...args] of preview.commands) await this.runCommand(command!, args)
  }

  private async uninstall(schedule: ScheduledJobDefinition): Promise<void> {
    const preview = this.preview(schedule)
    if (schedule.backend === 'task-scheduler') {
      await this.safeRun('schtasks.exe', ['/Delete', '/TN', this.windowsTaskName(schedule.id), '/F'])
    } else if (schedule.backend === 'launch-agent') {
      const plist = preview.files[0]?.path
      if (plist) {
        await this.safeRun('launchctl', ['bootout', `gui/${this.uid}`, plist])
        rmSync(plist, { force: true })
      }
    } else {
      const timerName = this.systemdBaseName(schedule.id) + '.timer'
      await this.safeRun('systemctl', ['--user', 'disable', '--now', timerName])
      for (const file of preview.files) rmSync(file.path, { force: true })
      await this.safeRun('systemctl', ['--user', 'daemon-reload'])
    }
  }

  private async safeRun(command: string, args: string[]): Promise<void> {
    try { await this.runCommand(command, args) } catch { /* idempotent uninstall */ }
  }

  private windowsTaskName(id: string): string {
    return `Media Experiment Ledger Studio\\${id}`
  }

  private windowsPreview(id: string, request: SaveScheduleRequest): SchedulerPreview {
    const args = ['/Create', '/TN', this.windowsTaskName(id), '/TR', `"${this.executablePath}" --mel-schedule=${id}`, '/F']
    if (request.cadence.kind === 'daily') args.push('/SC', 'DAILY', '/ST', clock(request.cadence.hour, request.cadence.minute))
    if (request.cadence.kind === 'weekly') {
      args.push('/SC', 'WEEKLY', '/D', weekdayNames(request.cadence.weekdays).map(day => day.toUpperCase()).join(','), '/ST', clock(request.cadence.hour, request.cadence.minute))
    }
    if (request.cadence.kind === 'interval') args.push('/SC', 'HOURLY', '/MO', String(request.cadence.hours))
    return { backend: 'task-scheduler', files: [], commands: [['schtasks.exe', ...args]] }
  }

  private macPreview(id: string, request: SaveScheduleRequest): SchedulerPreview {
    const label = `io.github.pme26elvis.media-experiment-ledger-studio.schedule.${id}`
    const path = join(this.homeDirectory, 'Library', 'LaunchAgents', `${label}.plist`)
    let scheduleXml = ''
    if (request.cadence.kind === 'interval') {
      scheduleXml = `<key>StartInterval</key><integer>${request.cadence.hours * 3600}</integer>`
    } else if (request.cadence.kind === 'daily') {
      scheduleXml = `<key>StartCalendarInterval</key><dict><key>Hour</key><integer>${request.cadence.hour}</integer><key>Minute</key><integer>${request.cadence.minute}</integer></dict>`
    } else {
      const cadence = request.cadence
      const entries = [...new Set(cadence.weekdays)].sort((a, b) => a - b).map(day =>
        `<dict><key>Weekday</key><integer>${day + 1}</integer><key>Hour</key><integer>${cadence.hour}</integer><key>Minute</key><integer>${cadence.minute}</integer></dict>`).join('')
      scheduleXml = `<key>StartCalendarInterval</key><array>${entries}</array>`
    }
    const content = `<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict><key>Label</key><string>${xml(label)}</string><key>ProgramArguments</key><array><string>${xml(this.executablePath)}</string><string>--mel-schedule=${xml(id)}</string></array>${scheduleXml}<key>ProcessType</key><string>Background</string></dict></plist>\n`
    return {
      backend: 'launch-agent',
      files: [{ path, content }],
      commands: [['launchctl', 'bootstrap', `gui/${this.uid}`, path]],
    }
  }

  private systemdBaseName(id: string): string {
    return `media-experiment-ledger-studio-${id}`
  }

  private linuxPreview(id: string, request: SaveScheduleRequest): SchedulerPreview {
    const base = this.systemdBaseName(id)
    const root = join(this.homeDirectory, '.config', 'systemd', 'user')
    const servicePath = join(root, `${base}.service`)
    const timerPath = join(root, `${base}.timer`)
    const service = `[Unit]\nDescription=Media Experiment Ledger Studio scheduled job ${id}\n\n[Service]\nType=oneshot\nExecStart=${systemdQuote(this.executablePath)} ${systemdQuote(`--mel-schedule=${id}`)}\n`
    let timerExpression = ''
    if (request.cadence.kind === 'interval') timerExpression = `OnUnitActiveSec=${request.cadence.hours}h\nOnBootSec=5m`
    if (request.cadence.kind === 'daily') timerExpression = `OnCalendar=*-*-* ${clock(request.cadence.hour, request.cadence.minute)}:00`
    if (request.cadence.kind === 'weekly') timerExpression = `OnCalendar=${weekdayNames(request.cadence.weekdays).join(',')} *-*-* ${clock(request.cadence.hour, request.cadence.minute)}:00`
    const timer = `[Unit]\nDescription=Media Experiment Ledger Studio schedule ${id}\n\n[Timer]\n${timerExpression}\nPersistent=true\nUnit=${base}.service\n\n[Install]\nWantedBy=timers.target\n`
    return {
      backend: 'systemd-user',
      files: [{ path: servicePath, content: service }, { path: timerPath, content: timer }],
      commands: [
        ['systemctl', '--user', 'daemon-reload'],
        ['systemctl', '--user', 'enable', '--now', `${base}.timer`],
      ],
    }
  }

  private readRegistry(): SchedulerRegistry {
    try {
      const parsed = JSON.parse(readFileSync(this.registryPath, 'utf8')) as SchedulerRegistry
      if (parsed.schemaVersion === 1 && Array.isArray(parsed.schedules)) return parsed
    } catch { /* first run */ }
    return { schemaVersion: 1, schedules: [] }
  }
}
