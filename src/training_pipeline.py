"""
Training Pipeline (multi-city)
--------------------------------
1. Fetches historical (features, targets) for ALL cities from the Hopsworks
   Feature Store.
2. Encodes city as a one-hot feature so a single model learns city-specific
   patterns.
3. Trains & evaluates several models (Ridge, Random Forest, LSTM).
4. Picks the best model by RMSE, computes SHAP values for the tree model,
   and pushes the winning model to the Hopsworks Model Registry.

Run:
    python src/training_pipeline.py
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
import shap

from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

HOPSWORKS_API_KEY = os.environ.get("HOPSWORKS_API_KEY")
FEATURE_GROUP_NAME = "aqi_features"
FEATURE_GROUP_VERSION = 6
MODEL_NAME = "aqi_forecast_model"

# Fixed, known city list (kept in sync with src/feature_pipeline.py and
# api/app.py) so the one-hot columns built here always match what the API
# builds at inference time, regardless of which cities happen to have rows
# in the current training data.
CITY_LIST = ["Islamabad", "Karachi", "Lahore"]

BASE_FEATURE_COLUMNS = [
    "pm25",
    "temperature", "humidity", "pressure", "wind_speed", "wind_deg", "clouds",
    "hour", "day", "day_of_week", "month", "aqi_change_rate",
]
CITY_COLUMNS = [f"city_{c}" for c in CITY_LIST]
FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + CITY_COLUMNS
TARGET_COLUMN = "aqi"


def add_city_dummies(df: pd.DataFrame) -> pd.DataFrame:
    for c in CITY_LIST:
        df[f"city_{c}"] = (df["city"] == c).astype(float)
    return df


def load_features_from_hopsworks() -> pd.DataFrame:
    import hopsworks

    project = hopsworks.login(api_key_value=HOPSWORKS_API_KEY)
    fs = project.get_feature_store()
    fg = fs.get_feature_group(name=FEATURE_GROUP_NAME, version=FEATURE_GROUP_VERSION)
    # Read from the online store rather than the offline Spark path, which
    # has been unreliable on the free tier. Since our primary key includes
    # event_time (not just city), every row is unique, so the online store
    # retains full history here rather than just the latest value per city.
    df = fg.read(online=True)
    df = add_city_dummies(df)
    df = df.dropna(subset=BASE_FEATURE_COLUMNS + [TARGET_COLUMN])
    return df, project


def make_train_test(df: pd.DataFrame):
    df = df.sort_values("event_time")
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    return X_train, X_test, y_train, y_test


def evaluate(y_true, y_pred) -> dict:
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def train_ridge(X_train, y_train, X_test, y_test):
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    model = Ridge(alpha=1.0)
    model.fit(X_train_s, y_train)
    preds = model.predict(X_test_s)
    metrics = evaluate(y_test, preds)
    return model, scaler, metrics


def train_random_forest(X_train, y_train, X_test, y_test):
    model = RandomForestRegressor(n_estimators=300, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    metrics = evaluate(y_test, preds)
    return model, metrics


def train_lstm(X_train, y_train, X_test, y_test):
    """Simple LSTM over the feature vector treated as a single-timestep sequence."""
    import tensorflow as tf
    from tensorflow.keras import layers, models

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    X_train_seq = X_train_s.reshape((X_train_s.shape[0], 1, X_train_s.shape[1]))
    X_test_seq = X_test_s.reshape((X_test_s.shape[0], 1, X_test_s.shape[1]))

    model = models.Sequential([
        layers.Input(shape=(1, X_train_s.shape[1])),
        layers.LSTM(32, activation="tanh"),
        layers.Dense(16, activation="relu"),
        layers.Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")
    model.fit(X_train_seq, y_train, epochs=50, batch_size=8, verbose=0)

    preds = model.predict(X_test_seq).flatten()
    metrics = evaluate(y_test, preds)
    return model, scaler, metrics


def compute_shap_summary(rf_model, X_train) -> dict:
    explainer = shap.TreeExplainer(rf_model)
    shap_values = explainer.shap_values(X_train)
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    importance = dict(zip(FEATURE_COLUMNS, mean_abs_shap.tolist()))
    return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))


def main():
    if not HOPSWORKS_API_KEY:
        print("Missing HOPSWORKS_API_KEY")
        sys.exit(1)

    print("Loading features from Hopsworks...")
    df, project = load_features_from_hopsworks()
    print(f"Loaded {len(df)} rows across cities: {sorted(df['city'].unique().tolist())}")

    if len(df) < 30:
        print(
            f"WARNING: only {len(df)} rows available across all cities. Models "
            "will train but results won't be meaningful yet — keep the hourly "
            "feature pipeline running for a few days/weeks before trusting "
            "these numbers."
        )

    X_train, X_test, y_train, y_test = make_train_test(df)

    results = {}

    print("Training Ridge Regression...")
    ridge_model, ridge_scaler, ridge_metrics = train_ridge(X_train, y_train, X_test, y_test)
    results["ridge"] = ridge_metrics
    print(ridge_metrics)

    print("Training Random Forest...")
    rf_model, rf_metrics = train_random_forest(X_train, y_train, X_test, y_test)
    results["random_forest"] = rf_metrics
    print(rf_metrics)

    try:
        print("Training LSTM...")
        lstm_model, lstm_scaler, lstm_metrics = train_lstm(X_train, y_train, X_test, y_test)
        results["lstm"] = lstm_metrics
        print(lstm_metrics)
    except Exception as e:
        print(f"Skipping LSTM (likely too little data or TF not installed): {e}")

    best_name = min(results, key=lambda k: results[k]["rmse"])
    print(f"\nBest model: {best_name} -> {results[best_name]}")

    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/metrics.json", "w") as f:
        json.dump(results, f, indent=2)

    shap_importance = compute_shap_summary(rf_model, X_train)
    with open("artifacts/shap_importance.json", "w") as f:
        json.dump(shap_importance, f, indent=2)
    print(f"SHAP feature importance: {shap_importance}")

    if best_name == "ridge":
        joblib.dump({"model": ridge_model, "scaler": ridge_scaler}, "artifacts/model.pkl")
        model_type = "sklearn_ridge"
    elif best_name == "random_forest":
        joblib.dump({"model": rf_model, "scaler": None}, "artifacts/model.pkl")
        model_type = "sklearn_random_forest"
    else:
        lstm_model.save("artifacts/lstm_model.keras")
        joblib.dump({"scaler": lstm_scaler}, "artifacts/model.pkl")
        model_type = "tensorflow_lstm"

    push_model_to_registry(project, model_type, results[best_name])


def push_model_to_registry(project, model_type: str, metrics: dict):
    mr = project.get_model_registry()

    model = mr.python.create_model(
        name=MODEL_NAME,
        metrics=metrics,
        description=f"AQI forecast model ({model_type}), multi-city: {', '.join(CITY_LIST)}",
    )
    model.save("artifacts")
    print(f"Model pushed to registry as '{MODEL_NAME}' with metrics {metrics}")


if __name__ == "__main__":
    main()