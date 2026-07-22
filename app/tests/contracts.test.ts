import { describe, expect, it } from 'vitest'
import { IPC } from '../src/shared/contracts'
describe('IPC contract',()=>{ it('uses a closed namespaced allowlist',()=>{ const values=Object.values(IPC); expect(new Set(values).size).toBe(values.length); expect(values.every(value=>value.startsWith('mel:'))).toBe(true) }) })
