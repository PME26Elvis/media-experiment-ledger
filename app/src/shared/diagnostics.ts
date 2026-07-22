const WINDOWS_PATH = /(?:[A-Za-z]:\\|\\\\)[^\s"'<>|]+/gu
const POSIX_PATH = /(?<![A-Za-z0-9])\/(?:Users|home|var|tmp|private|mnt|media|opt|srv|run|Volumes)\/[^\s"'<>]+/gu
const EMAIL = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/giu
const BEARER = /\bBearer\s+[A-Za-z0-9._~+\/-]+=*/giu
const SECRET_ASSIGNMENT = /\b(?:api[_-]?key|token|secret|password|authorization|cookie)\s*[:=]\s*[^\s,;]+/giu
const LONG_TOKEN = /\b(?:sk|ghp|github_pat|AIza|nvapi|sess|key)[-_A-Za-z0-9]{12,}\b/gu
const URL = /https?:\/\/[^\s"'<>]+/gu

function redactUrl(value: string): string {
  try {
    const url = new URL(value)
    url.username = ''
    url.password = ''
    url.search = url.search ? '?[REDACTED]' : ''
    url.hash = ''
    return url.toString()
  } catch {
    return '[REDACTED_URL]'
  }
}

export function redactText(value: string): string {
  return value
    .replace(BEARER, 'Bearer [REDACTED]')
    .replace(SECRET_ASSIGNMENT, match => `${match.split(/[:=]/u, 1)[0]}=[REDACTED]`)
    .replace(LONG_TOKEN, '[REDACTED_TOKEN]')
    .replace(EMAIL, '[REDACTED_EMAIL]')
    .replace(WINDOWS_PATH, '[REDACTED_PATH]')
    .replace(POSIX_PATH, '[REDACTED_PATH]')
    .replace(URL, redactUrl)
    .slice(0, 8000)
}

const SENSITIVE_KEYS = /(?:secret|password|token|api[_-]?key|authorization|cookie|credential|prompt|path|url|email|user)/iu

export function redactValue(value: unknown, key = '', depth = 0): unknown {
  if (depth > 12) return '[MAX_DEPTH]'
  if (SENSITIVE_KEYS.test(key)) {
    if (/prompt/iu.test(key) && typeof value === 'string') {
      return { redacted: true, length: value.length }
    }
    return '[REDACTED]'
  }
  if (typeof value === 'string') return redactText(value)
  if (typeof value === 'number' || typeof value === 'boolean' || value === null || value === undefined) return value
  if (Array.isArray(value)) return value.slice(0, 1000).map(item => redactValue(item, key, depth + 1))
  if (typeof value === 'object') {
    const output: Record<string, unknown> = {}
    for (const [childKey, childValue] of Object.entries(value as Record<string, unknown>).slice(0, 1000)) {
      output[childKey] = redactValue(childValue, childKey, depth + 1)
    }
    return output
  }
  return String(value)
}

export function containsSecretLikeValue(value: unknown): boolean {
  const serialized = JSON.stringify(value)
  return Boolean(
    serialized.match(BEARER)
    || serialized.match(SECRET_ASSIGNMENT)
    || serialized.match(LONG_TOKEN)
    || serialized.match(EMAIL)
    || serialized.match(WINDOWS_PATH)
    || serialized.match(POSIX_PATH),
  )
}
