import { createHash } from 'node:crypto'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import { runWasmPostprocessor } from '../src/main/wasm-postprocessor'

// Exports fixed one-page memory, alloc(len) -> 0 and postprocess(ptr,len) -> packed(0,len).
// The host therefore receives exactly the JSON bytes it wrote, while still exercising the ABI.
const IDENTITY_WASM = Buffer.from(
  '0061736d01000000010c0260017f017f60027f7f017e0303020001050401010101072003066d656d6f7279020005616c6c6f6300000b706f737470726f6365737300010a0c02040041000b05002001ad0b',
  'hex',
)

const roots: string[] = []
function temporaryRoot(): string {
  const root = mkdtempSync(join(tmpdir(), 'mel-wasm-'))
  roots.push(root)
  return root
}
afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true })
})

describe('runWasmPostprocessor', () => {
  it('runs a pinned import-free module inside the worker ABI', async () => {
    const path = join(temporaryRoot(), 'identity.wasm')
    writeFileSync(path, IDENTITY_WASM)
    const sha256 = createHash('sha256').update(IDENTITY_WASM).digest('hex')
    const result = await runWasmPostprocessor({
      modulePath: path,
      sha256,
      input: { boxes: [{ x: 1, y: 2, score: 0.9 }] },
      timeoutMs: 1000,
      maxMemoryPages: 1,
    })
    expect(result.output).toEqual({ boxes: [{ x: 1, y: 2, score: 0.9 }] })
    expect(result.memoryPages).toBe(1)
    expect(result.moduleSha256).toBe(sha256)
  })

  it('rejects a module when its pinned hash does not match', async () => {
    const path = join(temporaryRoot(), 'identity.wasm')
    writeFileSync(path, IDENTITY_WASM)
    await expect(runWasmPostprocessor({ modulePath: path, sha256: '0'.repeat(64), input: {} }))
      .rejects.toThrow(/does not match/u)
  })
})
