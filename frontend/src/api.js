const BASE_URL = '/api'

async function get(path) {
  const res = await fetch(`${BASE_URL}${path}`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || `Request to ${path} failed (${res.status})`)
  }
  return res.json()
}

export const api = {
  current: () => get('/current'),
  forecast: () => get('/forecast'),
  shap: () => get('/shap'),
  metrics: () => get('/metrics'),
}
