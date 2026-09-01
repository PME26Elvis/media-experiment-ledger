import { createWriteStream } from 'node:fs'
import { spawn } from 'node:child_process'

const [, , logPath, ...command] = process.argv
if (!logPath || command.length === 0) {
  console.error('Usage: node run-and-log.mjs <log-path> <command...>')
  process.exit(2)
}

const log = createWriteStream(logPath, { flags: 'w' })
const child = spawn(command[0], command.slice(1), {
  shell: process.platform === 'win32',
  env: process.env,
  stdio: ['inherit', 'pipe', 'pipe'],
})

for (const stream of [child.stdout, child.stderr]) {
  stream.on('data', (chunk) => {
    process.stdout.write(chunk)
    log.write(chunk)
  })
}

child.on('error', (error) => {
  const text = `${error.stack ?? error.message}\n`
  process.stderr.write(text)
  log.write(text)
  log.end(() => process.exit(1))
})

child.on('exit', (code, signal) => {
  if (signal) log.write(`\nTerminated by signal ${signal}\n`)
  log.end(() => process.exit(code ?? 1))
})
