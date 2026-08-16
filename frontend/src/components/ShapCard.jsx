import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function ShapCard({ shapData }) {
  if (!shapData) return null

  const data = Object.entries(shapData)
    .map(([feature, value]) => ({ feature, importance: Number(value.toFixed(3)) }))
    .slice(0, 8)

  return (
    <div className="card">
      <h2>Feature Importance (SHAP)</h2>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} layout="vertical" margin={{ left: 20 }}>
          <XAxis type="number" stroke="#a8a196" fontSize={11} fontFamily="IBM Plex Mono, monospace" />
          <YAxis
            dataKey="feature"
            type="category"
            stroke="#a8a196"
            fontSize={11}
            fontFamily="IBM Plex Mono, monospace"
            width={80}
          />
          <Tooltip
            contentStyle={{
              background: '#1b222c',
              border: '1px solid #2a3441',
              borderRadius: 8,
              fontFamily: 'IBM Plex Mono, monospace',
              fontSize: 12,
            }}
          />
          <Bar dataKey="importance" fill="#d98e3f" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}