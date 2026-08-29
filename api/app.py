"""
Flask API (multi-city, OpenWeather-only data)
------------------------------------------------
Loads the latest model from the Hopsworks Model Registry and the latest
features from the Feature Store, and serves:
  GET  /api/health
  GET  /api/cities                 -> list of tracked cities
  GET  /api/current?city=Karachi   -> latest raw AQI + weather reading
  GET  /api/forecast?city=Karachi  -> 3-day AQI forecast
  GET  /api/shap                   -> SHAP feature importance (from last training run)
  GET  /api/metrics                -> model comparison metrics

Run:
    python api/app.py
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

HOPSWORKS_API_KEY = os.environ.get("HOPSWORKS_API_KEY")
FEATURE_GROUP_NAME = "aqi_features"
FEATURE_GROUP_VERSION = 6
MODEL_NAME = "aqi_forecast_model"

# Must match src/feature_pipeline.py and src/training_pipeline.py.
CITIES = [
    {"name": "Karachi", "lat": 24.8607, "lon": 67.0011},
    {"name": "Lahore", "lat": 31.5497, "lon": 74.3436},
    {"name": "Islamabad", "lat": 33.6844, "lon": 73.0479},
]
CITY_LIST = ["Islamabad", "Karachi", "Lahore"]  # alphabetical, matches training
DEFAULT_CITY = "Karachi"

BASE_FEATURE_COLUMNS = [
    "pm25",
    "temperature", "humidity", "pressure", "wind_speed", "wind_deg", "clouds",
    "hour", "day", "day_of_week", "month", "aqi_change_rate",
]
CITY_COLUMNS = [f"city_{c}" for c in CITY_LIST]
FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + CITY_COLUMNS

AQI_BREAKPOINTS = [
    (0, 50, "Good", "#00e400"),
    (51, 100, "Moderate", "#ffff00"),
    (101, 150, "Unhealthy for Sensitive Groups", "#ff7e00"),
    (151, 200, "Unhealthy", "#ff0000"),
    (201, 300, "Very Unhealthy", "#8f3f97"),
    (301, 500, "Hazardous", "#7e0023"),
]

AQI_DESCRIPTIONS = {
    "Good": "Air quality is satisfactory, and air pollution poses little or no risk.",
    "Moderate": "Air quality is acceptable. Some pollutants may be a moderate concern for a small number of unusually sensitive people.",
    "Unhealthy for Sensitive Groups": "Members of sensitive groups may experience health effects. The general public is less likely to be affected.",
    "Unhealthy": "Everyone may begin to experience health effects; sensitive groups may experience more serious effects.",
    "Very Unhealthy": "Health alert: everyone may experience more serious health effects.",
    "Hazardous": "Health warning of emergency conditions: everyone is more likely to be affected.",
}

# --- EPA AQI breakpoints, duplicated here (also in src/aqi_calc.py) so the
# API has no cross-directory import dependency. AQI is derived from real
# pollutant concentrations via the published EPA formula, not fabricated.
PM25_BREAKPOINTS = [
    (0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200), (150.5, 250.4, 201, 300),
    (250.5, 350.4, 301, 400), (350.5, 500.4, 401, 500),
]
PM10_BREAKPOINTS = [
    (0, 54, 0, 50), (55, 154, 51, 100), (155, 254, 101, 150),
    (255, 354, 151, 200), (355, 424, 201, 300),
    (425, 504, 301, 400), (505, 604, 401, 500),
]


def _sub_index(conc, breakpoints):
    if conc is None or (isinstance(conc, float) and np.isnan(conc)):
        return None
    conc = max(0.0, float(conc))
    for lo, hi, aqi_lo, aqi_hi in breakpoints:
        if lo <= conc <= hi:
            return ((aqi_hi - aqi_lo) / (hi - lo)) * (conc - lo) + aqi_lo
    return 500.0


def dominant_pollutant_for(pm25, pm10):
    """Given stored pm25/pm10 concentrations, report which one drives the
    AQI value (the one with the higher EPA sub-index), matching how real
    monitoring stations report a dominant pollutant."""
    pm25_aqi = _sub_index(pm25, PM25_BREAKPOINTS)
    pm10_aqi = _sub_index(pm10, PM10_BREAKPOINTS)
    candidates = [(v, name) for v, name in [(pm25_aqi, "PM2.5"), (pm10_aqi, "PM10")] if v is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[0])[1]


app = Flask(__name__)
CORS(app)

_cache = {"project": None, "model_bundle": None}


def get_hopsworks_project():
    import hopsworks
    if _cache["project"] is None:
        _cache["project"] = hopsworks.login(api_key_value=HOPSWORKS_API_KEY)
    return _cache["project"]


def get_latest_features_for_city(city: str, n=1) -> pd.DataFrame:
    project = get_hopsworks_project()
    fs = project.get_feature_store()
    fg = fs.get_feature_group(name=FEATURE_GROUP_NAME, version=FEATURE_GROUP_VERSION)
    # Read from the online store — a fast direct database lookup that
    # doesn't depend on the offline Spark materialization job, which has
    # been unreliable on the free tier. Online writes happen independently
    # of that job, so this stays available even when offline reads/writes
    # report failures.
    df = fg.read(online=True)
    df = df[df["city"] == city].sort_values("event_time")
    return df.tail(n)


def add_city_dummies(row: pd.DataFrame, city: str) -> pd.DataFrame:
    for c in CITY_LIST:
        row[f"city_{c}"] = 1.0 if c == city else 0.0
    return row


def get_model_bundle():
    if _cache["model_bundle"] is not None:
        return _cache["model_bundle"]

    project = get_hopsworks_project()
    mr = project.get_model_registry()
    # Use the most recently trained model, not "best by RMSE" — early
    # single-city models had misleadingly perfect scores due to overfitting
    # on very small datasets, which would otherwise keep winning forever.
    all_versions = mr.get_models(MODEL_NAME)
    model = max(all_versions, key=lambda m: m.version)
    model_dir = model.download()

    bundle_path = os.path.join(model_dir, "model.pkl")
    bundle = joblib.load(bundle_path)

    lstm_path = os.path.join(model_dir, "lstm_model.keras")
    if os.path.exists(lstm_path):
        import tensorflow as tf
        bundle["lstm"] = tf.keras.models.load_model(lstm_path)

    _cache["model_bundle"] = bundle
    return bundle


def predict_one(bundle, feature_row: pd.DataFrame) -> float:
    X = feature_row[FEATURE_COLUMNS]
    if "lstm" in bundle:
        X_s = bundle["scaler"].transform(X)
        X_seq = X_s.reshape((X_s.shape[0], 1, X_s.shape[1]))
        pred = bundle["lstm"].predict(X_seq, verbose=0).flatten()[0]
    elif bundle["scaler"] is not None:
        X_s = bundle["scaler"].transform(X)
        pred = bundle["model"].predict(X_s)[0]
    else:
        pred = bundle["model"].predict(X)[0]
    return float(pred)


def classify_aqi(aqi: float) -> dict:
    for low, high, label, color in AQI_BREAKPOINTS:
        if low <= aqi <= high:
            return {
                "level": label,
                "color": color,
                "hazardous": aqi > 150,
                "description": AQI_DESCRIPTIONS.get(label, ""),
            }
    return {"level": "Unknown", "color": "#999999", "hazardous": False, "description": ""}


def resolve_city() -> str:
    city = request.args.get("city", DEFAULT_CITY)
    valid_names = [c["name"] for c in CITIES]
    return city if city in valid_names else DEFAULT_CITY


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})


@app.route("/api/cities")
def cities():
    return jsonify({"cities": CITIES})


@app.route("/api/current")
def current():
    city = resolve_city()
    df = get_latest_features_for_city(city, n=1)
    if df.empty:
        return jsonify({"error": f"No data yet for {city}"}), 404
    row = df.iloc[0]

    pm25 = float(row["pm25"]) if pd.notna(row["pm25"]) else None
    pm10 = float(row["pm10"]) if pd.notna(row["pm10"]) else None

    result = {
        "city": city,
        "event_time": str(row["event_time"]),
        "aqi": float(row["aqi"]),
        "dominant_pollutant": dominant_pollutant_for(pm25, pm10),
        "pm25": pm25,
        "pm10": pm10,
        "o3": float(row["o3"]) if pd.notna(row["o3"]) else None,
        "no2": float(row["no2"]) if pd.notna(row["no2"]) else None,
        "so2": float(row["so2"]) if pd.notna(row["so2"]) else None,
        "co": float(row["co"]) if pd.notna(row["co"]) else None,
        "temperature": float(row["temperature"]),
        "humidity": float(row["humidity"]),
        "pressure": float(row["pressure"]) if pd.notna(row["pressure"]) else None,
        "wind_speed": float(row["wind_speed"]),
        "clouds": float(row["clouds"]) if pd.notna(row["clouds"]) else None,
    }
    result["alert"] = classify_aqi(result["aqi"])
    return jsonify(result)


@app.route("/api/forecast")
def forecast():
    city = resolve_city()
    df = get_latest_features_for_city(city, n=1)
    if df.empty:
        return jsonify({"error": f"No data yet for {city}"}), 404

    latest_row = df.iloc[[0]].copy()
    latest_row = add_city_dummies(latest_row, city)
    bundle = get_model_bundle()

    forecasts = []
    base_time = datetime.now(timezone.utc)
    working_row = latest_row.copy()

    for day_offset in range(1, 4):
        future_time = base_time + timedelta(days=day_offset)
        working_row["hour"] = future_time.hour
        working_row["day"] = future_time.day
        working_row["day_of_week"] = future_time.weekday()
        working_row["month"] = future_time.month

        pred_aqi = predict_one(bundle, working_row)
        forecasts.append({
            "date": future_time.strftime("%Y-%m-%d"),
            "predicted_aqi": round(pred_aqi, 1),
            "alert": classify_aqi(pred_aqi),
        })

        working_row["aqi_change_rate"] = pred_aqi - working_row["aqi"].values[0]
        working_row["aqi"] = pred_aqi

    return jsonify({"city": city, "forecast": forecasts})


@app.route("/api/shap")
def shap_importance():
    path = os.path.join("artifacts", "shap_importance.json")
    if not os.path.exists(path):
        return jsonify({"error": "No SHAP data yet. Run training_pipeline.py first."}), 404
    with open(path) as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/api/metrics")
def metrics():
    path = os.path.join("artifacts", "metrics.json")
    if not os.path.exists(path):
        return jsonify({"error": "No metrics yet. Run training_pipeline.py first."}), 404
    with open(path) as f:
        data = json.load(f)
    return jsonify(data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)