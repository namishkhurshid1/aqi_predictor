// Stylized (non-geographic) visual panel showing the three tracked cities as
// clickable pins. Positions are illustrative, not accurate coordinates.
const CITY_POSITIONS = {
  Islamabad: { x: 62, y: 22 },
  Lahore: { x: 68, y: 45 },
  Karachi: { x: 30, y: 82 },
}

export default function PakistanMap({ cities, selectedCity, cityColors, onSelectCity }) {
  if (!cities || !cities.length) return null

  return (
    <div className="pak-map">
      <svg viewBox="0 0 100 100" className="pak-map-svg" preserveAspectRatio="xMidYMid meet">
        <defs>
          <radialGradient id="pakGlow" cx="50%" cy="50%" r="70%">
            <stop offset="0%" stopColor="#1b2350" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#0c1024" stopOpacity="0" />
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="100" height="100" fill="url(#pakGlow)" />

        {/* decorative grid lines to suggest a monitoring panel, not a real map */}
        {[20, 40, 60, 80].map((v) => (
          <line key={`h${v}`} x1="0" y1={v} x2="100" y2={v} stroke="rgba(255,255,255,0.05)" strokeWidth="0.3" />
        ))}
        {[20, 40, 60, 80].map((v) => (
          <line key={`v${v}`} x1={v} y1="0" x2={v} y2="100" stroke="rgba(255,255,255,0.05)" strokeWidth="0.3" />
        ))}

        {cities.map((c) => {
          const pos = CITY_POSITIONS[c.name] || { x: 50, y: 50 }
          const isSelected = c.name === selectedCity
          const color = cityColors?.[c.name] || '#7c6cf0'

          return (
            <g
              key={c.name}
              transform={`translate(${pos.x}, ${pos.y})`}
              onClick={() => onSelectCity(c.name)}
              style={{ cursor: 'pointer' }}
            >
              {isSelected && (
                <circle r="6" fill={color} opacity="0.18">
                  <animate attributeName="r" values="6;9;6" dur="2.2s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.18;0.05;0.18" dur="2.2s" repeatCount="indefinite" />
                </circle>
              )}
              <circle r={isSelected ? 3.2 : 2.2} fill={color} stroke="#0c1024" strokeWidth="0.6" />
              <text
                x="0"
                y={isSelected ? -6 : -4.5}
                textAnchor="middle"
                fontSize={isSelected ? 4.2 : 3.4}
                fontFamily="IBM Plex Mono, monospace"
                fontWeight={isSelected ? 700 : 500}
                fill={isSelected ? '#fff' : '#a8a196'}
              >
                {c.name}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}