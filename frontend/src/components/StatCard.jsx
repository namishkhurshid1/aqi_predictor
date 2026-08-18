export default function StatCard({ label, big, sub, pill, pillColor }) {
  return (
    <div className="stat-card">
      <div className="label">{label}</div>
      <div className="row">
        <div className="big">{big}</div>
        {pill && (
          <span className="pill" style={{ background: `${pillColor}22`, color: pillColor }}>
            {pill}
          </span>
        )}
      </div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  )
}