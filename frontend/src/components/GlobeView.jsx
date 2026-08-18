import { useEffect, useRef } from 'react'
import Globe from 'globe.gl'

// A real interactive rotating globe (Three.js under the hood via globe.gl),
// with a single marker over the current city, colored by live AQI severity.
export default function GlobeView({ lat, lon, color, city }) {
  const containerRef = useRef(null)
  const globeRef = useRef(null)

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

    globe.controls().autoRotate = true
    globe.controls().autoRotateSpeed = 0.6
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
    if (!globe || lat === undefined || lon === undefined) return

    globe
      .pointsData([{ lat, lng: lon, city, color }])
      .pointLat('lat')
      .pointLng('lng')
      .pointColor('color')
      .pointAltitude(0.02)
      .pointRadius(0.6)
      .pointLabel((d) => `${d.city}`)
      .pointOfView({ lat, lng: lon, altitude: 1.8 }, 1200)
  }, [lat, lon, color, city])

  return <div ref={containerRef} className="globe-wrap" />
}