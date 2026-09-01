function windowsPathPattern(): RegExp {
  return /(?:[A-Za-z]:\\+|\\\\)[^\s"'<>|]+/gu
}

function posixPathPattern(): RegExp {
  return /(?<![A-Za-z0-9])\/(?:Users|home|var|tmp|private|mnt|media|opt|srv|run|Volumes)\/[^\s"'<>]+/gu
}

function emailPattern(): RegExp {
  return /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/giu
}

function bearerPattern(): RegExp {
  return /\bBearer\s+[A-Za-z0-9._~+\/-]+=*/giu
}

function secretAssignmentPattern(): RegExp {
  return /\b(?:api[_-]?key|token|secret|password|authorization|cookie)\s*[:=]\s*[^\s,;]+/giu
}

function dangerousSecretAssignmentPattern(): RegExp {
  return /\b(?:api[_-]?key|token|secret|password|authorization|cookie)\s*[:=]\s*[A-Za-z0-9._~+\/-]{8,}/iu
}

function longTokenPattern(): RegExp {
  return /\b(?:sk|ghp|github_pat|AIza|nvapi|sess|key)[-_A-Za-z0-9]{12,}\b/gu
}

function httpUrlPattern(): RegExp {
  return /https?:\/\/[^\s"'<>]+/gu
}

function redactUrl(value: string): string {
  try {
    const parsed = new globalThis.URL(value)
    parsed.username = ''
    parsed.password = ''
    parsed.search = parsed.search ? '?redacted=1' : ''
    parsed.hash = ''
    return parsed.toString()
  } catch {
    return '[REDACTED_URL]'
  }
}

export function redactText(value: string): string {
  return value
    .replace(httpUrlPattern(), redactUrl)
    .replace(bearerPattern(), 'Bearer [REDACTED]')
    .replace(secretAssignmentPattern(), match => `${match.split(/[:=]/u, 1)[0]}=[REDACTED]`)
    .replace(longTokenPattern(), '[REDACTED_TOKEN]')
    .replace(emailPattern(), '[REDACTED_EMAIL]')
    .replace(windowsPathPattern(), '[REDACTED_PATH]')
    .replace(posixPathPattern(), '[REDACTED_PATH]')
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
    .replaceAll('[REDACTED]', '')
    .replaceAll('[REDACTED_TOKEN]', '')
    .replaceAll('[REDACTED_EMAIL]', '')
    .replaceAll('[REDACTED_PATH]', '')
    .replaceAll('[REDACTED_URL]', '')
  return bearerPattern().test(serialized)
    || dangerousSecretAssignmentPattern().test(serialized)
    || longTokenPattern().test(serialized)
    || emailPattern().test(serialized)
    || windowsPathPattern().test(serialized)
    || posixPathPattern().test(serialized)
}
