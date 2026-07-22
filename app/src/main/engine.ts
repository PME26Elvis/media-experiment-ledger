import { app } from 'electron'
import { access } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { spawn } from 'node:child_process'
import { createInterface } from 'node:readline'

export interface EngineEvent {
  type: 'progress' | 'result' | 'error' | 'log'
  stage?: string
  progress?: number
  completed?: number
  total?: number
  data?: Record<string, unknown>
  message?: string
}

export function engineSourceRoot(): string {
  return join(app.getAppPath(), 'engine')
}

export function packagedEngineExecutable(): string {
  return join(
    process.resourcesPath,
    'engine-bin',
    'mel-engine',
    process.platform === 'win32' ? 'mel-engine.exe' : 'mel-engine',
  )
}

export async function engineReady(): Promise<boolean> {
  try {
    await access(
      app.isPackaged
        ? packagedEngineExecutable()
        : join(engineSourceRoot(), 'mel_engine', '__main__.py'),
    )
    return true
  } catch {
    return false
  }
}

function developmentPython(): string {
  if (process.env.MEL_PYTHON) return process.env.MEL_PYTHON
  return process.platform === 'win32' ? 'python' : 'python3'
}

export function runEngine(
  payload: Record<string, unknown>,
  onEvent: (event: EngineEvent) => void,
  signal: AbortSignal,
  environment: Record<string, string> = {},
): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const executable = app.isPackaged
      ? packagedEngineExecutable()
      : developmentPython()
    const args = app.isPackaged ? [] : ['-m', 'mel_engine']
    const cwd = app.isPackaged ? dirname(executable) : engineSourceRoot()
    const env = app.isPackaged
      ? { ...process.env, ...environment }
      : {
          ...process.env,
          ...environment,
          PYTHONPATH: engineSourceRoot(),
        }
    const child = spawn(executable, args, {
      cwd,
      env,
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
      shell: false,
    })
    let finalResult: Record<string, unknown> | undefined
    const stdout = createInterface({ input: child.stdout })
    stdout.on('line', (line) => {
      try {
        const event = JSON.parse(line) as EngineEvent
        onEvent(event)
        if (event.type === 'result') finalResult = event.data ?? {}
        if (event.type === 'error') {
          reject(new Error(event.message ?? 'Engine error'))
        }
      } catch {
        onEvent({ type: 'log', message: line })
      }
    })
    child.stderr.on('data', (chunk) => {
      onEvent({ type: 'log', message: String(chunk).trim() })
    })
    child.on('error', reject)
    child.on('exit', (code) => {
      if (code === 0) resolve(finalResult ?? {})
      else reject(new Error(`Engine exited with code ${code}`))
    })
    signal.addEventListener('abort', () => child.kill(), { once: true })
    child.stdin.write(`${JSON.stringify(payload)}\n`)
    child.stdin.end()
  })
}
