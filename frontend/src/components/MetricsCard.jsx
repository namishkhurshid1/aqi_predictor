export default function MetricsCard({ metrics }) {
  if (!metrics) return null

  return (
    <div className="card">
      <h2>Model Comparison</h2>
      {Object.entries(metrics).map(([name, m]) => (
        <div key={name} className="model-block">
          <div className="model-name">{name.replace('_', ' ')}</div>
          <div className="metrics-row">
            <div className="metric">
              <div className="label">RMSE</div>
              <div className="value">{m.rmse.toFixed(2)}</div>
            </div>
            <div className="metric">
              <div className="label">MAE</div>
              <div className="value">{m.mae.toFixed(2)}</div>
            </div>
            <div className="metric">
              <div className="label">R²</div>
              <div className="value">{m.r2.toFixed(2)}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}