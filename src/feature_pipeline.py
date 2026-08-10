"""
Feature Pipeline
-----------------
1. Fetches raw weather data (OpenWeather) and pollution/AQI data (AQICN) for a city.
2. Computes model-input features (time-based + derived) and the target (AQI).
3. Writes the resulting feature row to a Hopsworks Feature Group.

Run manually first to validate:
    python src/feature_pipeline.py

Environment variables required (set locally in a .env file, and as GitHub Secrets
for automated runs):
    HOPSWORKS_API_KEY
    AQICN_TOKEN
    OPENWEATHER_API_KEY
    CITY_NAME        e.g. "Karachi"
    CITY_LAT         e.g. 24.8607
    CITY_LON         e.g. 67.0011
"""

import os
import sys
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone

# ---- Load .env locally (no-op in GitHub Actions, where secrets are injected directly) ----
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

AQICN_TOKEN = os.environ.get("AQICN_TOKEN")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
HOPSWORKS_API_KEY = os.environ.get("HOPSWORKS_API_KEY")
CITY_NAME = os.environ.get("CITY_NAME", "Karachi")
CITY_LAT = float(os.environ.get("CITY_LAT", 24.8607))
CITY_LON = float(os.environ.get("CITY_LON", 67.0011))

FEATURE_GROUP_NAME = "aqi_features"
FEATURE_GROUP_VERSION = 4


def fetch_aqi_data(city: str) -> dict:
    """Fetch current AQI + pollutant breakdown from AQICN."""
    url = f"https://api.waqi.info/feed/{city}/?token={AQICN_TOKEN}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "ok":
        raise RuntimeError(f"AQICN API error: {data}")

    d = data["data"]
    iaqi = d.get("iaqi", {})

    return {
        "aqi": d.get("aqi"),
        "pm25": iaqi.get("pm25", {}).get("v"),
        "pm10": iaqi.get("pm10", {}).get("v"),
        "o3": iaqi.get("o3", {}).get("v"),
        "no2": iaqi.get("no2", {}).get("v"),
        "so2": iaqi.get("so2", {}).get("v"),
        "co": iaqi.get("co", {}).get("v"),
        "station_time": d.get("time", {}).get("iso"),
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
    """AQICN omits some pollutants for some cities (returns None). Cast to a
    real float / NaN so pandas + Hopsworks infer a proper numeric dtype
    instead of an all-null column, which Hopsworks' schema check rejects."""
    if value is None:
        return np.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def build_feature_row(aqi_data: dict, weather_data: dict, previous_aqi: float | None) -> pd.DataFrame:
    """Combine raw data into a single feature row with time-based + derived features."""
    now = datetime.now(timezone.utc)

    row = {
        "event_time": now,
        "city": CITY_NAME,
        # --- raw pollutant / weather features ---
        "aqi": _to_float(aqi_data["aqi"]),
        "pm25": _to_float(aqi_data["pm25"]),
        "pm10": _to_float(aqi_data["pm10"]),
        "o3": _to_float(aqi_data["o3"]),
        "no2": _to_float(aqi_data["no2"]),
        "so2": _to_float(aqi_data["so2"]),
        "co": _to_float(aqi_data["co"]),
        "temperature": weather_data["temperature"],
        "humidity": weather_data["humidity"],
        "pressure": weather_data["pressure"],
        "wind_speed": weather_data["wind_speed"],
        "wind_deg": weather_data["wind_deg"],
        "clouds": weather_data["clouds"],
        # --- time-based features ---
        "hour": now.hour,
        "day": now.day,
        "day_of_week": now.weekday(),
        "month": now.month,
        # --- derived features ---
        "aqi_change_rate": (
            (aqi_data["aqi"] - previous_aqi) if previous_aqi is not None else 0.0
        ),
    }
    df = pd.DataFrame([row])

    float_cols = [
        "aqi", "pm25", "pm10", "o3", "no2", "so2", "co",
        "temperature", "humidity", "pressure", "wind_speed", "wind_deg",
        "clouds", "aqi_change_rate",
    ]
    df[float_cols] = df[float_cols].astype("float64")
    return df


def get_previous_aqi(fg) -> float | None:
    """Look up the most recent AQI value already stored, to compute change rate."""
    try:
        df = fg.read()
        if df.empty:
            return None
        df = df.sort_values("event_time")
        return float(df.iloc[-1]["aqi"])
    except Exception as e:
        print(f"Could not read previous AQI (likely first run): {e}")
        return None


def push_to_feature_store(df: pd.DataFrame):
    import hopsworks

    project = hopsworks.login(api_key_value=HOPSWORKS_API_KEY)
    fs = project.get_feature_store()

    fg = fs.get_or_create_feature_group(
        name=FEATURE_GROUP_NAME,
        version=FEATURE_GROUP_VERSION,
        description="AQI + weather features for forecasting",
        primary_key=["city", "event_time"],
        event_time="event_time",
        time_travel_format="HUDI",
    )

    # Recompute change rate using the true previous value from the store
    previous_aqi = get_previous_aqi(fg)
    df["aqi_change_rate"] = df["aqi"].iloc[0] - previous_aqi if previous_aqi is not None else 0.0

    try:
        fg.insert(df, wait=True)
        print(f"Inserted 1 row into '{FEATURE_GROUP_NAME}' (v{FEATURE_GROUP_VERSION}) for {CITY_NAME}.")
    except Exception as e:
        # Hopsworks' materialization job sometimes reports "FAILED" via its
        # job-status API even though the underlying Hudi write committed
        # successfully (confirmed by checking the feature group's commit
        # history in the Hopsworks UI). Treat this specific case as a
        # warning rather than a hard failure so the pipeline doesn't
        # falsely alarm on every run.
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
            ("AQICN_TOKEN", AQICN_TOKEN),
            ("OPENWEATHER_API_KEY", OPENWEATHER_API_KEY),
            ("HOPSWORKS_API_KEY", HOPSWORKS_API_KEY),
        ] if not val
    ]
    if missing:
        print(f"Missing required environment variables: {missing}")
        sys.exit(1)

    print(f"Fetching data for {CITY_NAME} ({CITY_LAT}, {CITY_LON})...")
    aqi_data = fetch_aqi_data(CITY_NAME)
    weather_data = fetch_weather_data(CITY_LAT, CITY_LON)

    df = build_feature_row(aqi_data, weather_data, previous_aqi=None)
    print(df.T)

    push_to_feature_store(df)


if __name__ == "__main__":
    main()