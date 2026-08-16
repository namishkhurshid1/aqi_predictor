// Drifting dot field behind the panel header. Count and opacity scale with
// the current AQI reading — a literal, not decorative, stand-in for
// particulate density in the air.
export default function HazeField({ aqi, color }) {
  const count = Math.max(6, Math.min(36, Math.round((aqi / 300) * 36) + 6))

  const dots = Array.from({ length: count }, (_, i) => {
    const size = 3 + Math.random() * 6
    const top = Math.random() * 100
    const left = Math.random() * 100
    const dur = 14 + Math.random() * 14
    const dx = (Math.random() - 0.5) * 120
    const dy = (Math.random() - 0.5) * 80
    const opacity = 0.15 + Math.random() * 0.3

    return (
      <span
        key={i}
        className="haze-dot"
        style={{
          width: size,
          height: size,
          top: `${top}%`,
          left: `${left}%`,
          '--dot-color': color,
          '--dot-opacity': opacity,
          '--dur': `${dur}s`,
          '--dx': `${dx}px`,
          '--dy': `${dy}px`,
        }}
      />
    )
  })

  return <div className="haze-field">{dots}</div>
}