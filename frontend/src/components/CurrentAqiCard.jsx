export default function CurrentAqiCard({ data }) {
  if (!data) return null
  const { aqi, alert, temperature, humidity, wind_speed, pm25, pm10, event_time } = data

  return (
    <div className="card">
      <h2>Current AQI</h2>
      <div className="current-aqi">
        <div className="aqi-badge" style={{ background: alert.color }}>
          {Math.round(aqi)}
        </div>
        <div className="aqi-meta">
          <div className="level">{alert.level}</div>
          <div className="sub">Updated {new Date(event_time).toLocaleString()}</div>
        </div>
      </div>

      <div className="metrics-row" style={{ marginTop: 20 }}>
        <div className="metric">
          <div className="label">PM2.5</div>
          <div className="value">{pm25 ?? '—'}</div>
        </div>
        <div className="metric">
          <div className="label">PM10</div>
          <div className="value">{pm10 ?? '—'}</div>
        </div>
        <div className="metric">
          <div className="label">Temp</div>
          <div className="value">{temperature}°C</div>
        </div>
        <div className="metric">
          <div className="label">Humidity</div>
          <div className="value">{humidity}%</div>
        </div>
        <div className="metric">
          <div className="label">Wind</div>
          <div className="value">{wind_speed} m/s</div>
        </div>
      </div>

      {alert.hazardous && (
        <div className="alert-banner">
          ⚠ Hazardous air quality detected. Limit outdoor exposure.
        </div>
      )}
    </div>
  )
}
