export default function ForecastCard({ forecast }) {
  if (!forecast || !forecast.length) return null

  return (
    <div className="card">
      <h2>3-Day Forecast</h2>
      <div className="forecast-list">
        {forecast.map((f) => (
          <div className="forecast-day" key={f.date}>
            <div className="date">
              {new Date(f.date).toLocaleDateString(undefined, {
                weekday: 'short',
                month: 'short',
                day: 'numeric',
              })}
            </div>
            <div className="aqi" style={{ color: f.alert.color }}>
              {Math.round(f.predicted_aqi)}
            </div>
            <div className="level">{f.alert.level}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
