import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts'

export default function ForecastChart({ current, forecast }) {
  if (!current || !forecast || !forecast.length) return null

  const data = [
    { date: 'Now', aqi: current.aqi },
    ...forecast.map((f) => ({ date: f.date, aqi: f.predicted_aqi })),
  ]

  return (
    <div className="card">
      <h2>AQI Trend</h2>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262b36" />
          <XAxis dataKey="date" stroke="#8b93a7" fontSize={12} />
          <YAxis stroke="#8b93a7" fontSize={12} />
          <Tooltip
            contentStyle={{ background: '#171a21', border: '1px solid #262b36' }}
          />
          <Line
            type="monotone"
            dataKey="aqi"
            stroke="#4f8cff"
            strokeWidth={2}
            dot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
