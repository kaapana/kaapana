// Turns a rejected request into a user-facing sentence and into the technical
// detail (status, request line, backend message, request id) for
// ErrorDetailsDialog. The Kaapana backends raise FastAPI HTTPExceptions, so the
// backend's own message is `response.data.detail`.

export interface ApiErrorInfo {
  /** HTTP status of the response, when one arrived. */
  status: number | null
  statusText: string | null
  /** Upper-case HTTP method and the request path, when known. */
  method: string | null
  url: string | null
  /** The backend's own message (`detail` for FastAPI). */
  detail: string | null
  /** A request identifier from the response headers, when the gateway adds one. */
  requestId: string | null
  /** The transport's message, e.g. "Network Error" or "timeout of 10000ms exceeded". */
  message: string | null
}

function detailToString(detail: unknown): string | null {
  if (typeof detail === 'string') return detail.trim() || null
  if (detail === null || detail === undefined) return null
  // FastAPI validation errors arrive as a list of {loc, msg, type}.
  if (Array.isArray(detail)) {
    const messages = detail
      .map((entry) => (entry && typeof entry === 'object' && 'msg' in entry ? String(entry.msg) : JSON.stringify(entry)))
      .filter(Boolean)
    return messages.length ? messages.join(' ') : null
  }
  try {
    return JSON.stringify(detail)
  } catch {
    return String(detail)
  }
}

/** The backend's own message for a failed request, or null when it gave none. */
export function apiErrorDetail(err: any): string | null {
  return detailToString(err?.response?.data?.detail)
}

/**
 * User-facing text for a failure. `fallback` must already be a complete,
 * user-facing sentence; the backend's message is appended when it exists,
 * since for the Kaapana backends it is usually the part that says what to do.
 */
export function apiErrorText(err: any, fallback: string): string {
  const detail = apiErrorDetail(err)
  return detail ? `${fallback} ${detail}` : fallback
}

/** Everything worth showing behind a "Details" disclosure. */
export function apiErrorInfo(err: any): ApiErrorInfo {
  const response = err?.response
  const config = err?.config
  const headers = response?.headers ?? {}
  const requestId = headers['x-request-id'] ?? headers['X-Request-Id'] ?? null
  return {
    status: typeof response?.status === 'number' ? response.status : null,
    statusText: response?.statusText || null,
    method: typeof config?.method === 'string' ? config.method.toUpperCase() : null,
    url: typeof config?.url === 'string' ? config.url : null,
    detail: apiErrorDetail(err),
    requestId: requestId ? String(requestId) : null,
    message: typeof err?.message === 'string' && err.message ? err.message : null,
  }
}

/** Plain-text rendering of the details, for copying into a bug report. */
export function formatApiErrorInfo(info: ApiErrorInfo, summary?: string): string {
  const lines: string[] = []
  if (summary) lines.push(summary)
  if (info.status !== null) lines.push(`Status: ${info.status}${info.statusText ? ` ${info.statusText}` : ''}`)
  if (info.method || info.url) lines.push(`Request: ${[info.method, info.url].filter(Boolean).join(' ')}`)
  if (info.detail) lines.push(`Backend message: ${info.detail}`)
  if (info.requestId) lines.push(`Request ID: ${info.requestId}`)
  if (info.message) lines.push(`Error: ${info.message}`)
  return lines.join('\n')
}
