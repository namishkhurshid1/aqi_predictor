export default function StatCard({ label, big, sub, pill, pillColor, icon }) {
  return (
    <div className="stat-card">
      <div className="stat-card-top">
        <div className="label">{label}</div>
        {icon && <div className="stat-icon" style={{ color: pillColor }}>{icon}</div>}
      </div>
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