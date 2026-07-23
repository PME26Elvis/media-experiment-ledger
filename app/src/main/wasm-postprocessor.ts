import { createHash } from 'node:crypto'
import { readFileSync, statSync } from 'node:fs'
import { resolve } from 'node:path'
import { Worker } from 'node:worker_threads'
import type {
  WasmPostprocessRequest,
  WasmPostprocessResult,
} from '../shared/integration-contracts'

const MAX_MODULE_BYTES = 16 * 1024 * 1024
const MAX_JSON_BYTES = 1024 * 1024

interface WorkerSuccess {
  ok: true
  output: unknown
  memoryPages: number
}

interface WorkerFailure {
  ok: false
  error: string
}

const WORKER_SOURCE = String.raw`
const { parentPort, workerData } = require('node:worker_threads')
;(async () => {
  try {
    const moduleBytes = Buffer.from(workerData.moduleBytes)
    const inputBytes = Buffer.from(workerData.inputBytes)
    const module = await WebAssembly.compile(moduleBytes)
    const imports = WebAssembly.Module.imports(module)
    if (imports.length !== 0) throw new Error('WASM imports are forbidden; WASI, network and host callbacks are unavailable.')
    const instance = await WebAssembly.instantiate(module, {})
    const memory = instance.exports.memory
    const alloc = instance.exports.alloc
    const postprocess = instance.exports.postprocess
    if (!(memory instanceof WebAssembly.Memory)) throw new Error('WASM module must export memory.')
    if (typeof alloc !== 'function' || typeof postprocess !== 'function') throw new Error('WASM module must export alloc and postprocess.')
    if (memory.buffer.byteLength / 65536 > workerData.maxMemoryPages) throw new Error('WASM memory exceeds the configured page limit.')
    const inputPointer = Number(alloc(inputBytes.byteLength))
    if (!Number.isSafeInteger(inputPointer) || inputPointer < 0 || inputPointer + inputBytes.byteLength > memory.buffer.byteLength) {
      throw new Error('WASM allocator returned an invalid input range.')
    }
    new Uint8Array(memory.buffer, inputPointer, inputBytes.byteLength).set(inputBytes)
    const packed = postprocess(inputPointer, inputBytes.byteLength)
    if (typeof packed !== 'bigint') throw new Error('postprocess must return an i64 packed pointer/length value.')
    const outputPointer = Number((packed >> 32n) & 0xffffffffn)
    const outputLength = Number(packed & 0xffffffffn)
    const memoryPages = memory.buffer.byteLength / 65536
    if (memoryPages > workerData.maxMemoryPages) throw new Error('WASM memory grew beyond the configured page limit.')
    if (outputLength < 0 || outputLength > workerData.maxJsonBytes) throw new Error('WASM output exceeds the JSON byte limit.')
    if (outputPointer < 0 || outputPointer + outputLength > memory.buffer.byteLength) throw new Error('WASM returned an invalid output range.')
    const text = Buffer.from(new Uint8Array(memory.buffer, outputPointer, outputLength)).toString('utf8')
    const output = JSON.parse(text)
    parentPort.postMessage({ ok: true, output, memoryPages })
  } catch (error) {
    parentPort.postMessage({ ok: false, error: error instanceof Error ? error.message : String(error) })
  }
})()
`

function sha256(bytes: Uint8Array): string {
  return createHash('sha256').update(bytes).digest('hex')
}

export async function runWasmPostprocessor(request: WasmPostprocessRequest): Promise<WasmPostprocessResult> {
  const modulePath = resolve(request.modulePath)
  const stat = statSync(modulePath)
  if (!stat.isFile()) throw new Error('WASM module path is not a file.')
  if (stat.size <= 0 || stat.size > MAX_MODULE_BYTES) throw new Error('WASM module size is outside the accepted range.')
  const moduleBytes = readFileSync(modulePath)
  const moduleSha256 = sha256(moduleBytes)
  if (moduleSha256 !== request.sha256.toLowerCase()) throw new Error('WASM module SHA-256 does not match the pinned manifest value.')

  const inputText = JSON.stringify(request.input)
  if (inputText === undefined) throw new Error('WASM input must be JSON serializable.')
  const inputBytes = Buffer.from(inputText, 'utf8')
  if (inputBytes.byteLength > MAX_JSON_BYTES) throw new Error('WASM input exceeds the JSON byte limit.')
  const timeoutMs = Math.min(Math.max(request.timeoutMs ?? 1_000, 50), 5_000)
  const maxMemoryPages = Math.min(Math.max(request.maxMemoryPages ?? 64, 1), 256)
  const started = performance.now()

  const result = await new Promise<WorkerSuccess>((resolvePromise, rejectPromise) => {
    const worker = new Worker(WORKER_SOURCE, {
      eval: true,
      workerData: { moduleBytes, inputBytes, maxMemoryPages, maxJsonBytes: MAX_JSON_BYTES },
    })
    let settled = false
    const settle = (operation: () => void): void => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      operation()
    }
    const timer = setTimeout(() => {
      settle(() => {
        void worker.terminate()
        rejectPromise(new Error(`WASM postprocessor exceeded the ${timeoutMs} ms timeout.`))
      })
    }, timeoutMs)
    worker.once('message', (message: WorkerSuccess | WorkerFailure) => {
      settle(() => {
        void worker.terminate()
        if (!message.ok) rejectPromise(new Error(`WASM postprocessor rejected: ${message.error}`))
        else resolvePromise(message)
      })
    })
    worker.once('error', error => settle(() => rejectPromise(new Error(`WASM worker failed: ${error.message}`))))
    worker.once('exit', code => {
      if (code !== 0) settle(() => rejectPromise(new Error(`WASM worker exited with code ${code}.`)))
    })
  })

  return {
    output: result.output,
    durationMs: Math.max(0, performance.now() - started),
    memoryPages: result.memoryPages,
    moduleSha256,
  }
}
