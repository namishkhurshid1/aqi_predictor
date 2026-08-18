export default function Navbar({ city, now }) {
  return (
    <div className="navbar">
      <div className="brand">
        <img src="/logo.png" alt="10Pearls" className="brand-logo" />
        Pearls AQI
      </div>
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