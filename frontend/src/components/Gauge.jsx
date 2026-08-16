// Instrument-style arc gauge. Sweeps 0-300 AQI across a 270deg arc.
export default function Gauge({ value, color, label }) {
  const size = 200
  const stroke = 12
  const r = (size - stroke) / 2
  const startAngle = -225 // degrees
  const sweep = 270
  const clamped = Math.max(0, Math.min(300, value))
  const pct = clamped / 300

  const polarToXY = (angleDeg) => {
    const a = (angleDeg * Math.PI) / 180
    return {
      x: size / 2 + r * Math.cos(a),
      y: size / 2 + r * Math.sin(a),
    }
  }

  const describeArc = (fromDeg, toDeg) => {
    const start = polarToXY(fromDeg)
    const end = polarToXY(toDeg)
    const largeArc = toDeg - fromDeg <= 180 ? 0 : 1
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`
  }

  const endAngle = startAngle + sweep * pct

  return (
    <div className="gauge-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <path
          d={describeArc(startAngle, startAngle + sweep)}
          fill="none"
          stroke="#2a3441"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        <path
          d={describeArc(startAngle, endAngle)}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        <text
          x="50%"
          y="48%"
          textAnchor="middle"
          className="gauge-value"
          dominantBaseline="middle"
        >
          {Math.round(value)}
        </text>
        <text
          x="50%"
          y="64%"
          textAnchor="middle"
          className="gauge-sub"
          fill="#a8a196"
        >
          AQI
        </text>
      </svg>
      <div className="gauge-label" style={{ color }}>
        {label}
      </div>
    </div>
  )
}