import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts'

export default function ForecastChart({ current, forecast, color }) {
  if (!current || !forecast || !forecast.length) return null

  const data = [
    { date: 'Now', aqi: current.aqi },
    ...forecast.map((f) => ({ date: f.date, aqi: f.predicted_aqi })),
  ]

  return (
    <div className="card">
      <h2>AQI Trend</h2>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="aqiFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a3441" />
          <XAxis
            dataKey="date"
            stroke="#a8a196"
            fontSize={11}
            fontFamily="IBM Plex Mono, monospace"
          />
          <YAxis stroke="#a8a196" fontSize={11} fontFamily="IBM Plex Mono, monospace" />
          <Tooltip
            contentStyle={{
              background: '#1b222c',
              border: '1px solid #2a3441',
              borderRadius: 8,
              fontFamily: 'IBM Plex Mono, monospace',
              fontSize: 12,
            }}
          />
          <Area
            type="monotone"
            dataKey="aqi"
            stroke={color}
            strokeWidth={2}
            fill="url(#aqiFill)"
            dot={{ r: 3, fill: color }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}