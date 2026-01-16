export const base = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/+$/, '')
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    public readonly fields: string[] = [],
  ) {
    super({
      DEVELOPMENT_IDENTITY_UNAVAILABLE: 'The local workspace owner is unavailable. See Help for setup.',
      DATABASE_UNAVAILABLE: 'The workspace database is unavailable.',
      RESUME_REVISION_CONFLICT: 'This resume changed in another session.',
      RESUME_NOT_FOUND: 'This resume is unavailable.',
      INVALID_REQUEST: 'Some fields need attention.',
      INVALID_RESUME_CONTENT: 'Some resume fields need attention.',
      REQUEST_TOO_LARGE: 'The resume exceeds the maximum request size.',
      UNSUPPORTED_EXPORT_CONTENT: 'This document exceeds export limits or contains unsupported characters. Try another format.',
      EXPORT_BUSY: 'The document renderer is busy. Try again shortly.',
      RESUME_EXPORT_NOT_FOUND: 'This export is no longer available.',
      OFFLINE: 'Could not reach the backend. Check that the local server is running.',
    }[code] ?? 'The request could not be completed.')
  }
}

export async function request<T>(url: string, method = 'GET', data?: unknown, signal?: AbortSignal, timeoutMs = 8000): Promise<T> {
  const timeout = AbortSignal.timeout(timeoutMs)
  try {
    const headers: Record<string, string> = { Accept: 'application/json' }
    if (data !== undefined) headers['Content-Type'] = 'application/json'
    const response = await fetch(base + url, {
      method,
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
      cache: 'no-store',
      headers,
      body: data === undefined ? undefined : JSON.stringify(data),
    })
    if (response.status === 204) return undefined as T
    if (!response.headers.get('content-type')?.includes('application/json')) {
      throw new ApiError(response.status, 'INVALID_RESPONSE')
    }
    const body = await response.json()
    if (!response.ok) {
      const details: unknown = body?.error?.fields
      const fields = Array.isArray(details) ? details.flatMap((item) => {
        const field: unknown = item?.field
        return Array.isArray(field) && field.every((part) => typeof part === 'string' || Number.isInteger(part))
          ? [field.filter((part) => !['body', 'content'].includes(String(part))).join(' / ')]
          : []
      }).filter(Boolean) : []
      throw new ApiError(response.status, body?.error?.code ?? 'HTTP_ERROR', [...new Set(fields)].slice(0, 5))
    }
    return body as T
  } catch (error) {
    if (error instanceof ApiError || signal?.aborted) throw error
    if (error instanceof SyntaxError) throw new ApiError(0, 'INVALID_RESPONSE')
    throw new ApiError(0, 'OFFLINE')
  }
}
