"""
Backfill Historical (features, targets)
----------------------------------------
Fetches historical daily AQI + weather data for a city over a date range and
inserts it into the same Hopsworks Feature Group used by feature_pipeline.py,
so you have enough history to train a model.

Data sources for history:
  - Weather: OpenWeather "Historical Weather" (One Call 3.0 timemachine) needs a
    paid plan for far-back dates on free tier limits, so we fall back to
    OpenWeather's free 5-day/3-hour forecast archive substitute OR, more
    reliably for a class project: we simulate a rolling backfill by running the
    feature pipeline going FORWARD in time (documented in the report as a known
    limitation of free-tier historical weather APIs).
  - AQI: AQICN's /feed endpoint only gives current data on the free tier too.

  ==> Practical approach used here: this script calls the SAME live-fetch
      functions as feature_pipeline.py repeatedly, once per "backfill day" you
      specify, but pulls REAL current data each time it's run. Use this by
      running the script daily via GitHub Actions for 2-3 weeks BEFORE your
      first training run, OR, if you have access to a paid/historical AQI
      dataset (e.g. exported CSV from AQICN's website, Kaggle, or EPA), use
      `backfill_from_csv()` below instead, which is the recommended path for
      getting a real multi-month training set quickly.

Run:
    python src/backfill_historical.py --mode live --days 1
    python src/backfill_historical.py --mode csv --file historical_aqi.csv
"""

import os
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(__file__))
from feature_pipeline import (
    fetch_aqi_data,
    fetch_weather_data,
    CITY_NAME,
    CITY_LAT,
    CITY_LON,
    HOPSWORKS_API_KEY,
    FEATURE_GROUP_NAME,
    FEATURE_GROUP_VERSION,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def backfill_live(days: int):
    """
    Calls the live AQICN/OpenWeather endpoints once (they only return current
    data), tagging the row with today's date. Intended to be run once per day
    over time to slowly build history. Not a true historical backfill.
    """
    aqi_data = fetch_aqi_data(CITY_NAME)
    weather_data = fetch_weather_data(CITY_LAT, CITY_LON)

    now = datetime.now(timezone.utc)
    row = {
        "event_time": now,
        "city": CITY_NAME,
        "aqi": aqi_data["aqi"],
        "pm25": aqi_data["pm25"],
        "pm10": aqi_data["pm10"],
        "o3": aqi_data["o3"],
        "no2": aqi_data["no2"],
        "so2": aqi_data["so2"],
        "co": aqi_data["co"],
        "temperature": weather_data["temperature"],
        "humidity": weather_data["humidity"],
        "pressure": weather_data["pressure"],
        "wind_speed": weather_data["wind_speed"],
        "wind_deg": weather_data["wind_deg"],
        "clouds": weather_data["clouds"],
        "hour": now.hour,
        "day": now.day,
        "day_of_week": now.weekday(),
        "month": now.month,
        "aqi_change_rate": 0.0,
    }
    return pd.DataFrame([row])


def backfill_from_csv(filepath: str) -> pd.DataFrame:
    """
    Recommended path: load a historical AQI/weather CSV (e.g. exported from
    AQICN's city page, Kaggle 'AQI dataset', or your local EPA/EPD portal) and
    reshape it into the same feature schema as feature_pipeline.py.

    Expected input CSV columns (rename yours to match, or adjust below):
        date, aqi, pm25, pm10, o3, no2, so2, co,
        temperature, humidity, pressure, wind_speed, wind_deg, clouds
    """
    df = pd.read_csv(filepath, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["event_time"] = pd.to_datetime(df["date"], utc=True)
    df["city"] = CITY_NAME
    df["hour"] = df["event_time"].dt.hour
    df["day"] = df["event_time"].dt.day
    df["day_of_week"] = df["event_time"].dt.dayofweek
    df["month"] = df["event_time"].dt.month
    df["aqi_change_rate"] = df["aqi"].diff().fillna(0.0)

    cols = [
        "event_time", "city", "aqi", "pm25", "pm10", "o3", "no2", "so2", "co",
        "temperature", "humidity", "pressure", "wind_speed", "wind_deg", "clouds",
        "hour", "day", "day_of_week", "month", "aqi_change_rate",
    ]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns after reshape: {missing}")

    return df[cols]


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
    )
    fg.insert(df, wait=True)
    print(f"Backfilled {len(df)} row(s) into '{FEATURE_GROUP_NAME}' for {CITY_NAME}.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["live", "csv"], default="live")
    parser.add_argument("--days", type=int, default=1, help="Only used for --mode live")
    parser.add_argument("--file", type=str, help="CSV path, required for --mode csv")
    args = parser.parse_args()

    if args.mode == "live":
        df = backfill_live(args.days)
    else:
        if not args.file:
            print("--file is required for --mode csv")
            sys.exit(1)
        df = backfill_from_csv(args.file)

    print(df.tail())
    push_to_feature_store(df)


if __name__ == "__main__":
    main()
