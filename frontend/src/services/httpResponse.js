/**
 * HTTP response helpers.
 * Provide defensive JSON parsing with clearer error messages.
 */

export async function readJsonResponse(response, requestLabel = 'Request') {
  const contentType = (response.headers.get('content-type') || '').toLowerCase()
  const isJson = contentType.includes('application/json')

  if (!response.ok) {
    let detail = response.statusText || 'Request failed'

    if (isJson) {
      try {
        const data = await response.json()
        detail = data?.detail || data?.message || detail
      } catch (_) {
        // Keep fallback detail
      }
    } else {
      try {
        const text = await response.text()
        if (text) {
          detail = text.slice(0, 160).replace(/\s+/g, ' ')
        }
      } catch (_) {
        // Keep fallback detail
      }
    }

    throw new Error(`${requestLabel} failed (${response.status}) [${response.url}]: ${detail}`)
  }

  if (!isJson) {
    let preview = ''
    try {
      preview = (await response.text()).slice(0, 120).replace(/\s+/g, ' ')
    } catch (_) {
      // ignore
    }
    throw new Error(
      `${requestLabel} expected JSON from [${response.url}] but received "${contentType || 'unknown'}"${preview ? `: ${preview}` : ''}`
    )
  }

  return response.json()
}
