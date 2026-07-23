import { describe, expect, it } from 'vitest'
import { containsSecretLikeValue, redactText, redactValue } from '../src/shared/diagnostics'

describe('diagnostics redaction', () => {
  it('removes credentials, emails, paths and URL query strings', () => {
    const raw = [
      'Authorization: Bearer sk-super-secret-token-value',
      'api_key=AIzaSuperSecretValue123456',
      'contact=user@example.com',
      'windows=C:\\Users\\Alice\\Projects\\private.json',
      'posix=/home/alice/project/private.json',
      'remote=https://user:password@example.com/path?token=secret#fragment',
    ].join(' ')
    const redacted = redactText(raw)
    expect(redacted).not.toContain('sk-super-secret-token-value')
    expect(redacted).not.toContain('AIzaSuperSecretValue123456')
    expect(redacted).not.toContain('user@example.com')
    expect(redacted).not.toContain('Alice')
    expect(redacted).not.toContain('/home/alice')
    expect(redacted).not.toContain('password')
    expect(redacted).not.toContain('token=secret')
    expect(redacted).toContain('[REDACTED]')
    expect(redacted).toContain('[REDACTED_PATH]')
  })

  it('redacts sensitive object keys and preserves non-sensitive structure', () => {
    const result = redactValue({
      status: 'failed',
      credential_profile_id: 'profile-id',
      prompt: 'draw a private scene',
      nested: { password: 'hunter2', attempts: 3 },
    }) as Record<string, unknown>
    expect(result.status).toBe('failed')
    expect(result.credential_profile_id).toBe('[REDACTED]')
    expect(result.prompt).toEqual({ redacted: true, length: 20 })
    expect(result.nested).toEqual({ password: '[REDACTED]', attempts: 3 })
  })

  it('accepts explicit redaction markers but rejects leaked secret-like values', () => {
    expect(containsSecretLikeValue({ error: 'api_key=[REDACTED] at [REDACTED_PATH]' })).toBe(false)
    expect(containsSecretLikeValue({ error: 'api_key=AIzaSuperSecretValue123456' })).toBe(true)
    expect(containsSecretLikeValue({ error: '/home/alice/private.txt' })).toBe(true)
  })
})
