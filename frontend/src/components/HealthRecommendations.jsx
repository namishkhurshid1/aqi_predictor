const ICONS = {
  exercise: (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="5.5" cy="17.5" r="3.5" />
      <circle cx="18.5" cy="17.5" r="3.5" />
      <path d="M12 17.5h4M5.5 17.5L9 9h5l3 4M9 9l2-3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  window: (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="3" width="18" height="18" rx="1.5" />
      <path d="M3 12h18M12 3v18" strokeLinecap="round" />
    </svg>
  ),
  mask: (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 10c0-3 3.5-5 8-5s8 2 8 5v3c0 3-3.5 5-8 5s-8-2-8-5v-3z" />
      <path d="M4 12h16M9 15c.6.6 1.8 1 3 1s2.4-.4 3-1" strokeLinecap="round" />
    </svg>
  ),
  purifier: (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="6" y="3" width="12" height="18" rx="2" />
      <path d="M9 7h6M9 11h6M9 15h6" strokeLinecap="round" />
    </svg>
  ),
  home: (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 11l8-7 8 7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M6 10v9a1 1 0 001 1h10a1 1 0 001-1v-9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
}

// Recommendations escalate with severity. Below AQI 100, nothing is shown
// at all — no precautions needed, nothing to render.
function getRecommendations(aqi) {
  const recs = []

  if (aqi > 100) {
    recs.push({ icon: 'exercise', text: 'Sensitive groups should reduce outdoor exercise' })
    recs.push({ icon: 'window', text: 'Close your windows to avoid dirty outdoor air' })
  }
  if (aqi > 150) {
    recs.push({ icon: 'mask', text: 'Sensitive groups should wear a mask outdoors' })
    recs.push({ icon: 'purifier', text: 'Sensitive groups should run an air purifier' })
  }
  if (aqi > 200) {
    recs.push({ icon: 'exercise', text: 'Everyone should avoid outdoor exercise' })
    recs.push({ icon: 'mask', text: 'Everyone should wear a mask outdoors' })
  }
  if (aqi > 300) {
    recs.push({ icon: 'home', text: 'Remain indoors — air quality is hazardous' })
  }

  return recs
}

export default function HealthRecommendations({ aqi }) {
  const recs = getRecommendations(aqi)
  if (!recs.length) return null

  return (
    <div className="card health-card">
      <h2>Health Recommendations</h2>
      <div className="health-list">
        {recs.map((r, i) => (
          <div className="health-item" key={i}>
            <div className="health-icon">{ICONS[r.icon]}</div>
            <div className="health-text">{r.text}</div>
          </div>
        ))}
      </div>
    </div>
  )
}