import { useEffect, useState } from 'react'
import { api } from './api'
import CurrentAqiCard from './components/CurrentAqiCard.jsx'
import ForecastCard from './components/ForecastCard.jsx'
import ForecastChart from './components/ForecastChart.jsx'
import ShapCard from './components/ShapCard.jsx'
import MetricsCard from './components/MetricsCard.jsx'

export default function App() {
  const [current, setCurrent] = useState(null)
  const [forecast, setForecast] = useState(null)
  const [shap, setShap] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  async function loadAll() {
    try {
      setLoading(true)
      setError(null)
      const [currentRes, forecastRes] = await Promise.all([
        api.current(),
        api.forecast(),
      ])
      setCurrent(currentRes)
      setForecast(forecastRes.forecast)

      // these are optional — dashboard still works before first training run
      api.shap().then(setShap).catch(() => setShap(null))
      api.metrics().then(setMetrics).catch(() => setMetrics(null))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAll()
    const interval = setInterval(loadAll, 5 * 60 * 1000) // refresh every 5 min
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="app">
      <div className="header">
        <h1>Pearls AQI Predictor</h1>
        <div className="city">{current?.city ?? ''}</div>
      </div>

      {loading && <div className="loading">Loading latest data...</div>}
      {error && (
        <div className="error">
          {error}
          <div style={{ marginTop: 8 }}>
            Make sure the Flask API is running on port 5000.
          </div>
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="grid">
            <CurrentAqiCard data={current} />
            <ForecastCard forecast={forecast} />
          </div>
          <div className="grid">
            <ForecastChart current={current} forecast={forecast} />
            <ShapCard shapData={shap} />
          </div>
          <MetricsCard metrics={metrics} />
        </>
      )}

      <div className="footer-note">
        Pearls AQI Predictor — serverless AQI forecasting pipeline
      </div>
    </div>
  )
}
