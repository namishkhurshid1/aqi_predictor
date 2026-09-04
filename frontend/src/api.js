const BASE_URL = import.meta.env.VITE_API_URL || '/api'

async function get(path) {
  const res = await fetch(`${BASE_URL}${path}`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || `Request to ${path} failed (${res.status})`)
  }
  return res.json()
}

export const api = {
  cities: () => get('/cities'),
  current: (city) => get(`/current?city=${encodeURIComponent(city)}`),
  forecast: (city) => get(`/forecast?city=${encodeURIComponent(city)}`),
  explain: (city) => get(`/explain?city=${encodeURIComponent(city)}`),
  shap: () => get('/shap'),
  metrics: () => get('/metrics'),
}