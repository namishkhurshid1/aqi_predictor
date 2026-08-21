export default function CityTabs({ cities, selectedCity, onSelectCity }) {
  if (!cities || !cities.length) return null

  return (
    <div className="city-tabs">
      {cities.map((c) => (
        <button
          key={c.name}
          className={`city-tab ${c.name === selectedCity ? 'active' : ''}`}
          onClick={() => onSelectCity(c.name)}
        >
          {c.name}
        </button>
      ))}
    </div>
  )
}