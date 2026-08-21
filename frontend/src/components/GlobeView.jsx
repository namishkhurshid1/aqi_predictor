import { useEffect, useRef } from 'react'
import Globe from 'globe.gl'

// Interactive rotating globe with one marker per tracked city. Clicking a
// marker calls onSelectCity with that city's name. The selected city's
// marker is drawn larger and in its live AQI color; the others are dimmed.
export default function GlobeView({ cities, selectedCity, cityColors, onSelectCity }) {
  const containerRef = useRef(null)
  const globeRef = useRef(null)
  const onSelectRef = useRef(onSelectCity)
  onSelectRef.current = onSelectCity

  useEffect(() => {
    if (!containerRef.current) return

    const globe = Globe()(containerRef.current)
      .globeImageUrl('https://unpkg.com/three-globe/example/img/earth-night.jpg')
      .backgroundColor('rgba(0,0,0,0)')
      .showAtmosphere(true)
      .atmosphereColor('#7c6cf0')
      .atmosphereAltitude(0.18)
      .width(containerRef.current.clientWidth)
      .height(containerRef.current.clientHeight)
      .onPointClick((point) => onSelectRef.current?.(point.name))

    globe.controls().autoRotate = true
    globe.controls().autoRotateSpeed = 0.5
    globe.controls().enableZoom = false

    globeRef.current = globe

    const handleResize = () => {
      if (containerRef.current) {
        globe.width(containerRef.current.clientWidth)
        globe.height(containerRef.current.clientHeight)
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      if (containerRef.current) containerRef.current.innerHTML = ''
    }
  }, [])

  useEffect(() => {
    const globe = globeRef.current
    if (!globe || !cities || !cities.length) return

    const points = cities.map((c) => {
      const isSelected = c.name === selectedCity
      return {
        lat: c.lat,
        lng: c.lon,
        name: c.name,
        color: cityColors?.[c.name] || '#7c6cf0',
        size: isSelected ? 0.9 : 0.5,
      }
    })

    globe
      .pointsData(points)
      .pointLat('lat')
      .pointLng('lng')
      .pointColor('color')
      .pointAltitude(0.02)
      .pointRadius('size')
      .pointLabel((d) => d.name)

    const selected = cities.find((c) => c.name === selectedCity)
    if (selected) {
      globe.pointOfView({ lat: selected.lat, lng: selected.lon, altitude: 1.9 }, 1200)
    }
  }, [cities, selectedCity, cityColors])

  return <div ref={containerRef} className="globe-wrap" />
}