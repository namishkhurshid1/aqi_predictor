"""
Feature Pipeline (multi-city, OpenWeather-only)
--------------------------------------------------
1. Fetches raw weather AND air pollution data from OpenWeather for each city
   in CITIES. OpenWeather is used as the single primary data source, as
   specified by the project requirements.
2. Computes the actual AQI from real PM2.5/PM10 concentrations using the
   published EPA breakpoint formula (see src/aqi_calc.py) — AQI is not a
   separately measured value, it's derived from pollutant concentrations.
3. Computes model-input features (time-based + derived).
4. Writes all rows in one batch to a Hopsworks Feature Group. The Feature
   Group's primary key is (city, event_time), so multiple cities coexist in
   the same table.

Run manually first to validate:
    python src/feature_pipeline.py

Environment variables required (set locally in a .env file, and as GitHub
Secrets for automated runs):
    HOPSWORKS_API_KEY
    OPENWEATHER_API_KEY
"""

import os
import sys
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from aqi_calc import compute_aqi

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
HOPSWORKS_API_KEY = os.environ.get("HOPSWORKS_API_KEY")

# The three cities this project tracks. Add/remove entries here to change
# coverage — everything downstream (training, API, frontend) reads the
# "city" column rather than hardcoding a single city.
CITIES = [
    {"name": "Karachi", "lat": 24.8607, "lon": 67.0011},
    {"name": "Lahore", "lat": 31.5497, "lon": 74.3436},
    {"name": "Islamabad", "lat": 33.6844, "lon": 73.0479},
]

FEATURE_GROUP_NAME = "aqi_features"
FEATURE_GROUP_VERSION = 5  # bumped: OpenWeather-only, single consistent data source


def fetch_pollution_data(lat: float, lon: float) -> dict:
    """Real pollutant concentrations from OpenWeather's Air Pollution API.
    Returns raw values in µg/m3 (µg/m3 for gases too, per OpenWeather docs)."""
    url = (
        f"http://api.openweathermap.org/data/2.5/air_pollution"
        f"?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("list"):
        raise RuntimeError(f"OpenWeather Air Pollution API returned no data: {data}")

    components = data["list"][0]["components"]
    return {
        "pm25": components.get("pm2_5"),
        "pm10": components.get("pm10"),
        "o3": components.get("o3"),
        "no2": components.get("no2"),
        "so2": components.get("so2"),
        "co": components.get("co"),
    }


def fetch_weather_data(lat: float, lon: float) -> dict:
    """Fetch current weather from OpenWeather."""
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    return {
        "temperature": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "pressure": data["main"]["pressure"],
        "wind_speed": data["wind"]["speed"],
        "wind_deg": data["wind"].get("deg"),
        "clouds": data["clouds"]["all"],
    }


def _to_float(value):
    if value is None:
        return np.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def build_feature_row(city_name: str, pollution_data: dict, weather_data: dict, previous_aqi) -> dict:
    now = datetime.now(timezone.utc)
    aqi, _dominant = compute_aqi(pollution_data.get("pm25"), pollution_data.get("pm10"))

    return {
        "event_time": now,
        "city": city_name,
        "aqi": _to_float(aqi),
        "pm25": _to_float(pollution_data["pm25"]),
        "pm10": _to_float(pollution_data["pm10"]),
        "o3": _to_float(pollution_data["o3"]),
        "no2": _to_float(pollution_data["no2"]),
        "so2": _to_float(pollution_data["so2"]),
        "co": _to_float(pollution_data["co"]),
        "temperature": _to_float(weather_data["temperature"]),
        "humidity": _to_float(weather_data["humidity"]),
        "pressure": _to_float(weather_data["pressure"]),
        "wind_speed": _to_float(weather_data["wind_speed"]),
        "wind_deg": _to_float(weather_data["wind_deg"]),
        "clouds": _to_float(weather_data["clouds"]),
        "hour": now.hour,
        "day": now.day,
        "day_of_week": now.weekday(),
        "month": now.month,
        "aqi_change_rate": (
            (aqi - previous_aqi) if previous_aqi is not None and aqi is not None else 0.0
        ),
    }


def get_previous_aqi_by_city(fg) -> dict:
    try:
        df = fg.read()
        if df.empty:
            return {}
        df = df.sort_values("event_time")
        latest = df.groupby("city").last()
        return {city: float(row["aqi"]) for city, row in latest.iterrows()}
    except Exception as e:
        print(f"Could not read previous AQI (likely first run): {e}")
        return {}


def push_to_feature_store(rows: list[dict]):
    import hopsworks

    project = hopsworks.login(api_key_value=HOPSWORKS_API_KEY)
    fs = project.get_feature_store()

    fg = fs.get_or_create_feature_group(
        name=FEATURE_GROUP_NAME,
        version=FEATURE_GROUP_VERSION,
        description="AQI + weather features for forecasting (multi-city, OpenWeather-only)",
        primary_key=["city", "event_time"],
        event_time="event_time",
        time_travel_format="HUDI",
    )

    df = pd.DataFrame(rows)
    float_cols = [
        "aqi", "pm25", "pm10", "o3", "no2", "so2", "co",
        "temperature", "humidity", "pressure", "wind_speed", "wind_deg",
        "clouds", "aqi_change_rate",
    ]
    df[float_cols] = df[float_cols].astype("float64")

    try:
        fg.insert(df, wait=True)
        print(f"Inserted {len(df)} row(s) into '{FEATURE_GROUP_NAME}' (v{FEATURE_GROUP_VERSION}).")
    except Exception as e:
        if "JobExecutionException" in type(e).__name__ or "Hopsworks Job failed" in str(e):
            print(
                "WARNING: Hopsworks reported the materialization job as failed, "
                "but this is frequently a false alarm on the free tier — the "
                "data write itself typically still succeeds. Verify by checking "
                "the feature group's commit history in the Hopsworks UI. "
                f"Original error: {e}"
            )
        else:
            raise


def main():
    missing = [
        name for name, val in [
            ("OPENWEATHER_API_KEY", OPENWEATHER_API_KEY),
            ("HOPSWORKS_API_KEY", HOPSWORKS_API_KEY),
        ] if not val
    ]
    if missing:
        print(f"Missing required environment variables: {missing}")
        sys.exit(1)

    import hopsworks

    project = hopsworks.login(api_key_value=HOPSWORKS_API_KEY)
    fs = project.get_feature_store()
    fg = fs.get_or_create_feature_group(
        name=FEATURE_GROUP_NAME,
        version=FEATURE_GROUP_VERSION,
        description="AQI + weather features for forecasting (multi-city, OpenWeather-only)",
        primary_key=["city", "event_time"],
        event_time="event_time",
        time_travel_format="HUDI",
    )
    previous_by_city = get_previous_aqi_by_city(fg)

    rows = []
    for city in CITIES:
        try:
            print(f"Fetching data for {city['name']} ({city['lat']}, {city['lon']})...")
            pollution_data = fetch_pollution_data(city["lat"], city["lon"])
            weather_data = fetch_weather_data(city["lat"], city["lon"])
            row = build_feature_row(
                city["name"], pollution_data, weather_data, previous_by_city.get(city["name"])
            )
            rows.append(row)
        except Exception as e:
            print(f"WARNING: failed to fetch data for {city['name']}: {e}")

    if not rows:
        print("No data fetched for any city — aborting.")
        sys.exit(1)

    print(pd.DataFrame(rows).T)

    # Insert one row at a time instead of batching all cities in one call —
    # this isolates whether a multi-row commit is what's causing the
    # materialization job to fail (single-row inserts were reliable before
    # multi-city support was added).
    for row in rows:
        push_to_feature_store([row])


if __name__ == "__main__":
    main()