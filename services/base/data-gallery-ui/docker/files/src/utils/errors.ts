// One place that turns a rejected request into text a user can act on.
//
// The guidelines ask for "what failed and, when possible, what the user can do
// next" rather than a status code. The Kaapana backend raises FastAPI
// HTTPExceptions, so the actionable part is `response.data.detail`; everything
// else falls back to the caller's own sentence rather than leaking `err.message`
// (which is where "Request failed with status code 409" comes from) or, worse,
// interpolating the Error object itself into the notification.
export function apiErrorDetail(err: any): string | null {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim() !== '') return detail.trim()
  return null
}

/** `fallback` must already be a complete, user-facing sentence. */
export function apiErrorText(err: any, fallback: string): string {
  const detail = apiErrorDetail(err)
  return detail ? `${fallback} ${detail}` : fallback
}
