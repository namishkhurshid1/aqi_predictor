import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

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
          <XAxis type="number" stroke="#8b93a7" fontSize={12} />
          <YAxis dataKey="feature" type="category" stroke="#8b93a7" fontSize={12} width={80} />
          <Tooltip
            contentStyle={{ background: '#171a21', border: '1px solid #262b36' }}
          />
          <Bar dataKey="importance" fill="#4f8cff" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
