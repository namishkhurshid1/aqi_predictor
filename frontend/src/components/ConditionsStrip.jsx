export default function ConditionsStrip({ data }) {
  if (!data) return null

  const cells = [
    { k: 'Temp', v: `${data.temperature?.toFixed(1)}°C` },
    { k: 'Humidity', v: `${data.humidity?.toFixed(0)}%` },
    { k: 'Wind', v: `${data.wind_speed?.toFixed(1)} m/s` },
    { k: 'Pressure', v: data.pressure ? `${data.pressure.toFixed(0)} hPa` : 'n/a' },
    { k: 'Clouds', v: data.clouds !== undefined ? `${data.clouds}%` : 'n/a' },
    { k: 'Updated', v: new Date(data.event_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) },
  ]

  return (
    <>
      <div className="strip-title">Conditions</div>
      <div className="strip">
        {cells.map((c) => (
          <div className="strip-cell" key={c.k}>
            <div className="k">{c.k}</div>
            <div className="v">{c.v}</div>
          </div>
        ))}
      </div>
    </>
  )
}