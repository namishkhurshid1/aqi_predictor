"""
EPA AQI calculation
--------------------
The Air Quality Index is not a separately measured quantity — it's derived
from raw pollutant concentrations using the US EPA's published breakpoint
formula. This module implements that formula for PM2.5 and PM10 (the two
pollutants that dominate AQI in South Asian cities), and picks whichever
pollutant produces the higher sub-index as the "dominant" pollutant, exactly
as real AQI monitoring stations do.

Reference: https://www.airnow.gov/aqi/aqi-calculator-concept/
"""

# (conc_low, conc_high, aqi_low, aqi_high) breakpoints, µg/m3
PM25_BREAKPOINTS = [
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
]

PM10_BREAKPOINTS = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 504, 301, 400),
    (505, 604, 401, 500),
]


def _sub_index(conc, breakpoints):
    if conc is None:
        return None
    conc = max(0.0, float(conc))
    for lo, hi, aqi_lo, aqi_hi in breakpoints:
        if lo <= conc <= hi:
            return ((aqi_hi - aqi_lo) / (hi - lo)) * (conc - lo) + aqi_lo
    # above the top breakpoint — clamp to max (extreme pollution event)
    return 500.0


def compute_aqi(pm25=None, pm10=None):
    """Returns (aqi, dominant_pollutant). Falls back gracefully if one of
    the two inputs is missing rather than fabricating a value."""
    pm25_aqi = _sub_index(pm25, PM25_BREAKPOINTS)
    pm10_aqi = _sub_index(pm10, PM10_BREAKPOINTS)

    candidates = [(v, name) for v, name in [(pm25_aqi, "PM2.5"), (pm10_aqi, "PM10")] if v is not None]
    if not candidates:
        return None, None

    aqi, dominant = max(candidates, key=lambda x: x[0])
    return round(aqi, 1), dominant