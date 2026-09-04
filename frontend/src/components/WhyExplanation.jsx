import { useEffect, useState } from 'react'
import { api } from '../api'

export default function WhyExplanation({ city }) {
  const [contributions, setContributions] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!city) return
    setContributions(null)
    setError(null)
    api.explain(city).then((res) => {
      setContributions(res.contributions || [])
    }).catch((e) => setError(e.message))
  }, [city])

  if (error) return null // fails silently — this is a bonus insight, not critical
  if (!contributions) return null
  if (!contributions.length) return null

  const maxAbs = Math.max(...contributions.map((c) => Math.abs(c.impact)), 1)

  return (
    <div className="card">
      <h2>Why This Reading? (Live SHAP Explanation)</h2>
      <p className="why-intro">
        These are the specific factors driving <strong>{city}</strong>'s current AQI
        prediction right now — not a generic average, but the actual contribution
        of each measurement in this exact reading.
      </p>
      <div className="why-list">
        {contributions.map((c) => {
          const pct = (Math.abs(c.impact) / maxAbs) * 100
          const positive = c.impact > 0
          return (
            <div className="why-row" key={c.feature}>
              <div className="why-label">
                {c.label}
                <span className="why-value">({c.value})</span>
              </div>
              <div className="why-bar-track">
                <div
                  className={`why-bar-fill ${positive ? 'up' : 'down'}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <div className={`why-impact ${positive ? 'up' : 'down'}`}>
                {positive ? '+' : ''}{c.impact} AQI
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}