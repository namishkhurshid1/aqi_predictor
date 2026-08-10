"""
Flask API
---------
Loads the latest model from the Hopsworks Model Registry and the latest
features from the Feature Store, and serves:
  GET  /api/health
  GET  /api/current       -> latest raw AQI + weather reading
  GET  /api/forecast      -> 3-day AQI forecast
  GET  /api/shap          -> SHAP feature importance (from last training run)
  GET  /api/alert         -> hazard alert level for the current AQI

Run:
    python api/app.py
    (serves on http://localhost:5000)
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify
from flask_cors import CORS

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

HOPSWORKS_API_KEY = os.environ.get("HOPSWORKS_API_KEY")
CITY_NAME = os.environ.get("CITY_NAME", "Karachi")
FEATURE_GROUP_NAME = "aqi_features"
FEATURE_GROUP_VERSION = 1
MODEL_NAME = "aqi_forecast_model"

FEATURE_COLUMNS = [
    "pm25", "pm10", "o3", "no2", "so2", "co",
    "temperature", "humidity", "pressure", "wind_speed", "wind_deg", "clouds",
    "hour", "day", "day_of_week", "month", "aqi_change_rate",
]

AQI_BREAKPOINTS = [
    (0, 50, "Good", "#00e400"),
    (51, 100, "Moderate", "#ffff00"),
    (101, 150, "Unhealthy for Sensitive Groups", "#ff7e00"),
    (151, 200, "Unhealthy", "#ff0000"),
    (201, 300, "Very Unhealthy", "#8f3f97"),
    (301, 500, "Hazardous", "#7e0023"),
]

app = Flask(__name__)
CORS(app)

_cache = {"project": None, "model_bundle": None, "model_dir": None}


def get_hopsworks_project():
    import hopsworks
    if _cache["project"] is None:
        _cache["project"] = hopsworks.login(api_key_value=HOPSWORKS_API_KEY)
    return _cache["project"]


def get_latest_features(n=1) -> pd.DataFrame:
    project = get_hopsworks_project()
    fs = project.get_feature_store()
    fg = fs.get_feature_group(name=FEATURE_GROUP_NAME, version=FEATURE_GROUP_VERSION)
    df = fg.read()
    df = df.sort_values("event_time")
    return df.tail(n)


def get_model_bundle():
    """Downloads (once, cached) the latest model version from the registry."""
    if _cache["model_bundle"] is not None:
        return _cache["model_bundle"]

    project = get_hopsworks_project()
    mr = project.get_model_registry()
    model = mr.get_best_model(MODEL_NAME, "rmse", "min")
    model_dir = model.download()
    _cache["model_dir"] = model_dir

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
            return {"level": label, "color": color, "hazardous": aqi > 150}
    return {"level": "Unknown", "color": "#999999", "hazardous": False}


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})


@app.route("/api/current")
def current():
    df = get_latest_features(n=1)
    if df.empty:
        return jsonify({"error": "No data yet"}), 404
    row = df.iloc[0]
    result = {
        "city": CITY_NAME,
        "event_time": str(row["event_time"]),
        "aqi": float(row["aqi"]),
        "pm25": float(row["pm25"]) if pd.notna(row["pm25"]) else None,
        "pm10": float(row["pm10"]) if pd.notna(row["pm10"]) else None,
        "temperature": float(row["temperature"]),
        "humidity": float(row["humidity"]),
        "wind_speed": float(row["wind_speed"]),
    }
    result["alert"] = classify_aqi(result["aqi"])
    return jsonify(result)


@app.route("/api/forecast")
def forecast():
    df = get_latest_features(n=1)
    if df.empty:
        return jsonify({"error": "No data yet"}), 404

    latest_row = df.iloc[[0]].copy()
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

        # feed prediction back in as the change-rate basis for the next day
        working_row["aqi_change_rate"] = pred_aqi - working_row["aqi"].values[0]
        working_row["aqi"] = pred_aqi

    return jsonify({"city": CITY_NAME, "forecast": forecasts})


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
    app.run(debug=True, port=5000)
