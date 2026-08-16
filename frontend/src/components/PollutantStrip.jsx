const POLLUTANTS = [
  { key: 'pm25', label: 'PM2.5', max: 250, color: '#d98e3f' },
  { key: 'pm10', label: 'PM10', max: 430, color: '#c6604f' },
  { key: 'o3', label: 'O3', max: 240, color: '#3e8e82' },
  { key: 'no2', label: 'NO2', max: 400, color: '#a8a196' },
  { key: 'so2', label: 'SO2', max: 500, color: '#d9a83f' },
  { key: 'co', label: 'CO', max: 30, color: '#8f7a6a' },
]

export default function PollutantStrip({ data }) {
  if (!data) return null

  return (
    <>
      <div className="strip-title">Pollutant Readout</div>
      <div className="strip">
        {POLLUTANTS.map((p) => {
          const raw = data[p.key]
          const hasValue = raw !== null && raw !== undefined && !Number.isNaN(raw)
          const pct = hasValue ? Math.min(100, (raw / p.max) * 100) : 0

          return (
            <div className="strip-cell" key={p.key}>
              <div className="k">{p.label}</div>
              <div className={`v ${hasValue ? '' : 'dim'}`}>
                {hasValue ? raw.toFixed(1) : 'n/a'}
              </div>
              <div className="bar">
                <div
                  className="bar-fill"
                  style={{ '--fill-pct': `${pct}%`, '--fill-color': p.color }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}