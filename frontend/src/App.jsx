import { useEffect, useState } from 'react'
import { api } from './api'
import Gauge from './components/Gauge.jsx'
import HazeField from './components/HazeField.jsx'
import PollutantStrip from './components/PollutantStrip.jsx'
import ConditionsStrip from './components/ConditionsStrip.jsx'
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
  const [now, setNow] = useState(new Date())

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
    const dataInterval = setInterval(loadAll, 5 * 60 * 1000)
    const clockInterval = setInterval(() => setNow(new Date()), 1000)
    return () => {
      clearInterval(dataInterval)
      clearInterval(clockInterval)
    }
  }, [])

  return (
    <div className="app">
      <div className="statusbar">
        <div className="brand">
          <span className="brand-mark" />
          <h1>Pearls AQI</h1>
          <span className="tag">Monitoring Station</span>
        </div>
        <div className="right">
          <span className="city">{current?.city ?? '—'}</span>
          <span>{now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
        </div>
      </div>

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
          <div className="panel-header">
            <HazeField aqi={current.aqi} color={current.alert.color} />
            <div className="panel-header-inner">
              <Gauge value={current.aqi} color={current.alert.color} label={current.alert.level} />
              <div>
                <div className="readout-eyebrow">Current Reading — {current.city}</div>
                <div className="readout-headline">
                  Air quality is{' '}
                  <span style={{ color: current.alert.color }}>{current.alert.level.toLowerCase()}</span>
                  {' '}right now.
                </div>
                {current.alert.hazardous && (
                  <div className="alert-banner">⚠ Limit outdoor exposure until levels drop.</div>
                )}
              </div>
            </div>
          </div>

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
        Pearls AQI Predictor — serverless forecasting pipeline · updates every hour
      </div>
    </div>
  )
}