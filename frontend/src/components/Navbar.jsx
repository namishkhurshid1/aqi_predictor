export default function Navbar({ city, now }) {
  return (
    <div className="navbar">
      <div className="brand">10Pearls AQI-Predictor</div>
      <nav>
        <span>Air Quality</span>
        <span>Forecast</span>
        <span>Insights</span>
      </nav>
      <div className="live-pill">
        <span className="dot" />
        {city ?? '—'} · {now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </div>
    </div>
  )
}