export interface HealthResponse {
  status: 'ok'
  application: string
  version: string
  environment: string
}

export class HealthError extends Error {
  constructor(public readonly kind: 'unavailable' | 'invalid', message: string) {
    super(message)
    this.name = 'HealthError'
  }
}

function isHealthResponse(value: unknown): value is HealthResponse {
  if (!value || typeof value !== 'object') return false
  const response = value as Record<string, unknown>
  return response.status === 'ok' &&
    ['application', 'version', 'environment'].every(
      (key) => typeof response[key] === 'string' && response[key].trim().length > 0,
    )
}

const baseUrl = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/+$/, '')

export async function fetchHealth(signal: AbortSignal): Promise<HealthResponse> {
  const controller = new AbortController()
  const abort = () => controller.abort()
  signal.addEventListener('abort', abort, { once: true })
  if (signal.aborted) controller.abort()
  // Bound the complete request, including reading its body.
  const timer = window.setTimeout(abort, 5000)
  try {
    const response = await fetch(`${baseUrl}/health`, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
      cache: 'no-store',
      credentials: 'omit',
    })
    if (!response.ok) {
      throw new HealthError('unavailable', `Backend returned HTTP ${response.status}.`)
    }
    if (!response.headers.get('content-type')?.includes('application/json')) {
      throw new HealthError('invalid', 'The backend did not return JSON.')
    }
    let body: unknown
    try {
      body = await response.json()
    } catch {
      if (controller.signal.aborted) throw new HealthError('unavailable', 'The request timed out or was cancelled.')
      throw new HealthError('invalid', 'The backend returned unreadable JSON.')
    }
    if (!isHealthResponse(body)) {
      throw new HealthError('invalid', 'The response does not match the health API contract.')
    }
    return body
  } catch (error) {
    if (error instanceof HealthError) throw error
    throw new HealthError('unavailable', 'Could not reach the backend within 5 seconds. Check that it is running.')
  } finally {
    window.clearTimeout(timer)
    signal.removeEventListener('abort', abort)
  }
}
