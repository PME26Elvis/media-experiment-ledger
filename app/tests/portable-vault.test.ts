import { describe, expect, it } from 'vitest'
import {
  decryptPortableVault,
  encryptPortableVault,
  type PortableVaultDocument,
} from '../src/main/portable-vault'

const testOptions = {
  iterations: 1,
  parallelism: 1,
  memorySizeKiB: 1024,
  hashLength: 32,
}

describe('portable vault', () => {
  it('round-trips a secret with Argon2id and XChaCha20-Poly1305', async () => {
    const document = await encryptPortableVault(
      'secret-value',
      'correct horse battery staple',
      testOptions,
    )
    expect(document.kdf.name).toBe('argon2id')
    expect(document.cipher.name).toBe('xchacha20-poly1305')
    expect(document.cipher.ciphertext).not.toContain('secret-value')
    await expect(decryptPortableVault(
      document,
      'correct horse battery staple',
    )).resolves.toBe('secret-value')
  })

  it('rejects invalid creation inputs and unsupported schemas', async () => {
    await expect(encryptPortableVault(
      '',
      'correct horse battery staple',
      testOptions,
    )).rejects.toThrow(/Secret value/u)
    await expect(encryptPortableVault(
      'secret',
      'short',
      testOptions,
    )).rejects.toThrow(/10 characters/u)
    await expect(decryptPortableVault(
      { schemaVersion: 2 } as unknown as PortableVaultDocument,
      'correct horse battery staple',
    )).rejects.toThrow(/Unsupported/u)
  })

  it('rejects a wrong password or modified ciphertext', async () => {
    const document = await encryptPortableVault(
      'secret-value',
      'correct horse battery staple',
      testOptions,
    )
    await expect(decryptPortableVault(
      document,
      'wrong password value',
    )).rejects.toThrow(/incorrect|modified/u)
    document.cipher.ciphertext = Buffer.from('tampered').toString('base64')
    await expect(decryptPortableVault(
      document,
      'correct horse battery staple',
    )).rejects.toThrow(/incorrect|modified/u)
  })
})
