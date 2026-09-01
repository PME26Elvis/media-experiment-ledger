import { describe, expect, it } from 'vitest'
import { IPC } from '../src/shared/contracts'
import { CUSTOM_MODEL_IPC } from '../src/shared/custom-model-contracts'
import { DIAGNOSTICS_IPC } from '../src/shared/diagnostics-contracts'
import { TEMPLATE_IPC } from '../src/shared/template-contracts'

describe('IPC contract', () => {
  it('uses one closed, namespaced and collision-free allowlist across every bridge', () => {
    const groups = [IPC, DIAGNOSTICS_IPC, TEMPLATE_IPC, CUSTOM_MODEL_IPC]
    const values = groups.flatMap(group => Object.values(group))
    expect(new Set(values).size).toBe(values.length)
    expect(values.every(value => value.startsWith('mel:'))).toBe(true)
    expect(values.every(value => !value.includes(' '))).toBe(true)
  })
})
