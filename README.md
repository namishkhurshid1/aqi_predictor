# Pearls AQI Predictor

End-to-end, 100%-serverless AQI forecasting system: automated data collection,
feature engineering, model training, and a real-time React dashboard.

## Architecture

```
Weather & Pollution APIs (OpenWeather, AQICN)
        │
        ▼
Feature Pipeline (src/feature_pipeline.py) ── hourly via GitHub Actions
        │
        ▼
Hopsworks Feature Store
        │
        ▼
Training Pipeline (src/training_pipeline.py) ── daily via GitHub Actions
   (Ridge, Random Forest, LSTM → best model + SHAP → Model Registry)
        │
        ▼
Flask API (api/app.py) ── serves predictions, SHAP, alerts
        │
        ▼
React Dashboard (frontend/) ── 3-day forecast, trend chart, SHAP chart, alerts
```

## 1. Prerequisites

- Python 3.11+
- Node.js 18+
- Free accounts: [Hopsworks](https://www.hopsworks.ai), [AQICN](https://aqicn.org/data-platform/token/), [OpenWeather](https://openweathermap.org/api)

## 2. Setup

```bash
# clone / unzip this project, then:
cp .env.example .env
# fill in .env with your real API keys and city coordinates

pip install -r requirements.txt
```

## 3. Run the pipelines manually (do this before automating)

```bash
# 1. Pull one row of live data into the feature store
python src/feature_pipeline.py

# 2. (Optional but recommended) backfill more history from a CSV,
#    e.g. a Kaggle AQI dataset or an export from AQICN's city page
python src/backfill_historical.py --mode csv --file historical_aqi.csv

# 3. Once you have enough rows (ideally 100+), train models
python src/training_pipeline.py
```

## 4. Run the dashboard locally

Terminal 1 — API:
```bash
python api/app.py
# serves on http://localhost:5000
```

Terminal 2 — React frontend:
```bash
cd frontend
npm install
npm run dev
# open http://localhost:5173
```

The Vite dev server proxies `/api/*` calls to the Flask backend, so the
dashboard works out of the box with no extra config.

## 5. Automate with GitHub Actions

1. Push this project to a GitHub repo.
2. Go to **Settings → Secrets and variables → Actions** and add:
   `AQICN_TOKEN`, `OPENWEATHER_API_KEY`, `HOPSWORKS_API_KEY`, `CITY_NAME`, `CITY_LAT`, `CITY_LON`
3. The workflows in `.github/workflows/` will then run automatically:
   - `feature_pipeline.yml` — every hour
   - `training_pipeline.yml` — every day at 02:00 UTC
4. You can also trigger either manually from the **Actions** tab (`workflow_dispatch`).

## 6. Deploying the dashboard (optional, for a live demo)

- **Frontend**: `npm run build` in `frontend/`, deploy the `dist/` folder to Vercel/Netlify (free tier).
- **API**: deploy `api/app.py` to Render/Railway free tier (both support Flask out of the box).
- Update `frontend/src/api.js`'s `BASE_URL` to point to your deployed API URL instead of `/api`.

## Notes on the "backfill" step

Both AQICN and OpenWeather's free tiers only expose **current** conditions, not
arbitrary historical data. For a real training set you have two options:

1. Let the hourly GitHub Action run for 1–2 weeks before training (simplest, but slow to start).
2. Use `backfill_historical.py --mode csv` with a historical AQI dataset (e.g. search Kaggle for
   "[your city] air quality dataset", or export data from your local environmental agency).
   This is the faster path and is worth mentioning as a design decision in your final report.

## Project checklist (maps to the assignment rubric)

- [x] Feature pipeline (fetch → compute → store)
- [x] Historical backfill
- [x] Training pipeline (Ridge, Random Forest, LSTM; RMSE/MAE/R²)
- [x] Model registry storage
- [x] CI/CD automation (GitHub Actions, hourly + daily)
- [x] Web dashboard (React + Flask) with 3-day forecast
- [x] SHAP feature importance
- [x] Hazardous AQI alerts
- [ ] EDA notebook — add your own exploration in `notebooks/eda.ipynb` once you have data
- [ ] Final report — document your findings, screenshots, and design decisions
