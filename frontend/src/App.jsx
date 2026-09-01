import { useEffect, useState } from 'react'
import { api } from './api'
import Navbar from './components/Navbar.jsx'
import PakistanMap from './components/PakistanMap.jsx'
import CityTabs from './components/CityTabs.jsx'
import StatCard from './components/StatCard.jsx'
import HealthRecommendations from './components/HealthRecommendations.jsx'
import PollutantStrip from './components/PollutantStrip.jsx'
import ConditionsStrip from './components/ConditionsStrip.jsx'
import ForecastCard from './components/ForecastCard.jsx'
import ForecastChart from './components/ForecastChart.jsx'
import ShapCard from './components/ShapCard.jsx'
import MetricsCard from './components/MetricsCard.jsx'

const FALLBACK_CITIES = [
  { name: 'Karachi', lat: 24.8607, lon: 67.0011 },
  { name: 'Lahore', lat: 31.5497, lon: 74.3436 },
  { name: 'Islamabad', lat: 33.6844, lon: 73.0479 },
]

export default function App() {
  const [cities, setCities] = useState(FALLBACK_CITIES)
  const [selectedCity, setSelectedCity] = useState('Karachi')
  const [current, setCurrent] = useState(null)
  const [forecast, setForecast] = useState(null)
  const [shap, setShap] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [now, setNow] = useState(new Date())
  const [cityColors, setCityColors] = useState({})

  useEffect(() => {
    api.cities().then((res) => {
      if (res.cities?.length) setCities(res.cities)
    }).catch(() => {})
  }, [])

  async function loadCity(city) {
    try {
      setLoading(true)
      setError(null)
      const [currentRes, forecastRes] = await Promise.all([
        api.current(city),
        api.forecast(city),
      ])
      setCurrent(currentRes)
      setForecast(forecastRes.forecast)
      setCityColors((prev) => ({ ...prev, [city]: currentRes.alert.color }))

      api.shap().then(setShap).catch(() => setShap(null))
      api.metrics().then(setMetrics).catch(() => setMetrics(null))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCity(selectedCity)
    const dataInterval = setInterval(() => loadCity(selectedCity), 5 * 60 * 1000)
    return () => clearInterval(dataInterval)
  }, [selectedCity])

  useEffect(() => {
    const clockInterval = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(clockInterval)
  }, [])

  const riskPct = current ? Math.min(100, Math.round((current.aqi / 300) * 100)) : 0

  return (
    <div className="app">
      <Navbar city={current?.city} now={now} />

      {loading && !current && <div className="loading">Reading sensor data…</div>}
      {error && (
        <div className="error">
          {error}
          <div style={{ marginTop: 8, fontSize: 11 }}>
            Make sure the Flask API is running.
          </div>
        </div>
      )}

      {current && (
        <>
          <div className="hero">
            <div>
              <div className="hero-eyebrow">Live Air Quality Monitoring</div>
              <h1>
                Air Quality <span>Index</span>
              </h1>
              <div className="hero-meta">
                {now.toLocaleDateString()} {now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · {current.city}
              </div>

              <CityTabs cities={cities} selectedCity={selectedCity} onSelectCity={setSelectedCity} />

              <div className="stat-cards">
                <StatCard
                  label="Main Statistics"
                  big={Math.round(current.aqi)}
                  sub={current.dominant_pollutant ? `Dominant pollutant: ${current.dominant_pollutant}` : 'Dominant pollutant: Unavailable'}
                  pill={current.alert.level}
                  pillColor={current.alert.color}
                />
                <StatCard
                  label="Risk of Pollution"
                  big={`${riskPct}%`}
                  sub={current.alert.description}
                  pill={current.alert.hazardous ? 'Hazardous' : 'Monitor'}
                  pillColor={current.alert.color}
                />
              </div>

              {current.alert.hazardous && (
                <div className="alert-banner">⚠ Limit outdoor exposure until levels drop.</div>
              )}
            </div>

            <PakistanMap
              cities={cities}
              selectedCity={selectedCity}
              cityColors={cityColors}
              onSelectCity={setSelectedCity}
            />
          </div>

          <HealthRecommendations aqi={current.aqi} />

          <PollutantStrip data={current} />
          <ConditionsStrip data={current} />

          <div className="grid">
            <ForecastCard forecast={forecast} />
            <ForecastChart current={current} forecast={forecast} color={current.alert.color} />
          </div>
          <div className="grid">
            <ShapCard shapData={shap} />
            <MetricsCard metrics={metrics} />
          </div>
        </>
      )}

      <div className="footer-note">
        10Pearls AeroSense — serverless AQI forecasting pipeline · updates every hour
      </div>
    </div>
  )
}