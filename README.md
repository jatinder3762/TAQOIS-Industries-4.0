# TAQOIS Industries 4.0 — Air Quality Command & Control

Cyberpunk-enterprise Streamlit platform for corridor-level air quality simulation, XGBoost-powered forecasting, real-time data ingestion, and operational intelligence across Canadian cities.

## What This App Does

TAQOIS monitors air-quality pressure across traffic and industrial corridors and converts that into actionable intelligence:

1. **Dashboard** — City-level status, hotspot counts, 3D geospatial risk map, threat matrix, and adaptive executive briefings.
2. **AI Forecast** — XGBoost ML predictions for 2, 4, and 6-hour horizons with confidence intervals and model explainability.
3. **Scenario Simulation** — Animated event cinema (wildfire, inversion, industrial incident, heatwave) with frame-by-frame playback, advisory generation, and simulation logs.

## Architecture

```
app.py                  Main Streamlit application (3 pages, sidebar controls)
forecast_engine.py      XGBoost forecasting engine (train/predict/feature importance)
data_ingestion.py       Real-time API integration (OpenWeatherMap + AQICN) with caching
database.py             SQLite persistence (predictions, actions, audit log)
```

## Corridors Covered

- **Toronto** — 15 corridors (Highway 401, Gardiner, DVP, Scarborough Industrial, etc.)
- **Vancouver** — 6 corridors (Broadway/Cambie, Hastings Industrial, etc.)
- **Montreal** — 6 corridors (Autoroute 40/Decarie, Ville-Marie, etc.)

## Features

### 1. Simulation Controls (Sidebar)

Sidebar controls available on all pages:

1. **City** — Switch between Toronto, Vancouver, Montreal
2. **Traffic Volume** (0–100)
3. **Weather Inversion** (0–100)
4. **Industrial Activity** (0–100)
5. **Wind Speed** (0–60 km/h)
6. **Humidity** (10–100%)
7. **Special Event / Incident Surge** — Toggle for emergency scenarios (e.g., chemical spill, warehouse fire, train derailment)

These inputs dynamically recalculate corridor risk and update all visuals in real time.

### 2. Dashboard

- **Metric Cards** — Citywide status, critical hotspots, peak corridor risk, primary drivers.
- **3D Corridor Map (PyDeck)** — Column height = risk intensity, color = severity band (green/cyan/amber/red). Hover for PM2.5, NO2, risk level.
- **Threat Matrix** — Sortable table with risk, PM2.5, NO2, exposure index per corridor.
- **Operational Intelligence** — Context-aware briefings (Executive, Tactical Response, Public Health Advisory) that adapt to current conditions.

### 3. AI Forecast (XGBoost)

- **ML Model** — 3 XGBoost regressors (risk_score, PM2.5, NO2) trained on 6000 synthetic corridor samples.
- **Horizons** — 2, 4, and 6-hour predictions with 95% confidence intervals.
- **Live Data Ingestion** — Fetch real-time weather and air quality from OpenWeatherMap and AQICN APIs.
- **Forecast Map** — 3D visualization of predicted risk per corridor.
- **Confidence Interval Chart** — Bar + marker chart showing prediction bounds.
- **Model Explainability** — Feature importance plots for risk_score and PM2.5.
- **Prediction History** — All forecasts stored in SQLite with audit trail.

### 4. Scenario Simulation (Cinema Mode)

- **5 Preset Scenarios** — Normal Operations, Wildfire/Smoke, Severe Inversion, Industrial Incident, Rush Hour + Heatwave.
- **48-Frame Animation** — 5 phases (Normal → Event Building → Peak Intensity → Sustained Impact → Recovery).
- **Real-Time Chart** — PM2.5 and risk score timeline that grows frame by frame.
- **Advisory System** — Automatic HIGH/SEVERE advisories triggered at threshold crossings.
- **Simulation Log** — Event-by-event log of phase transitions, alerts, and playback controls.
- **Adjustable Speed** — 0.5x, 1x, 2x, 3x playback.

### 5. Decision Support Intelligence

The `generate_intel()` engine produces adaptive briefings based on:

- Driver ranking (traffic, inversion, industrial — sorted by current pressure)
- Wind speed and humidity analysis
- Emergency event detection
- Forecast-aware notes when risk exceeds thresholds

### 6. Database & Audit

SQLite persistence via `database.py`:

- **predictions** — Every forecast stored with corridor, horizon, risk, PM2.5, NO2, confidence.
- **actions** — Auto-generated escalation actions for SEVERE corridors.
- **audit_log** — System events (model training, data fetches, etc.).

## Tech Stack

1. Python 3.10+
2. Streamlit 1.44+
3. XGBoost 2.0+
4. scikit-learn 1.4+
5. Pandas / NumPy
6. PyDeck (3D maps)
7. Plotly (charts)
8. Requests (API calls)
9. python-dotenv
10. SQLite3

## Local Setup

### 1. Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure API keys

Copy `env.example` to `.env` and add your keys:

```
OPENWEATHER_API_KEY=your_openweathermap_key
AQICN_API_TOKEN=your_aqicn_token
```

Free tier keys work. The app falls back to synthetic data if keys are missing.

### 4. Run the app

```powershell
streamlit run app.py
```

## How To Use

### Dashboard Demo

1. Select a city from the sidebar.
2. Adjust Traffic, Weather Inversion, and Industrial sliders.
3. Watch metric cards and 3D map update in real time.
4. Read the Executive Briefing and Tactical Response tabs.

### AI Forecast Demo

1. Navigate to AI Forecast page.
2. Model trains automatically on first load.
3. Optionally fetch live data via the expander button.
4. Switch between 2h, 4h, 6h horizons.
5. Review confidence intervals and feature importance charts.

### Scenario Simulation Demo

1. Navigate to Scenario Simulation page.
2. Pick a scenario (e.g., Wildfire / Smoke Event).
3. Press Auto Run — watch the animation unfold.
4. Observe advisory generation and phase transitions in the log.

## How The Models Work

### Deterministic Simulation Engine

For each corridor, the engine combines:

1. Emissions pressure drivers: traffic, inversion, industrial load.
2. Weather modifiers: wind speed and humidity.
3. Corridor sensitivity and population index.
4. Emergency event penalty.

Outputs: risk score (0–100), risk level, PM2.5/NO2 estimates, exposure index.

### XGBoost Forecast Engine

1. Generates 6000 synthetic training samples across all corridors.
2. Trains 3 separate XGBoost regressors (risk_score, pm25, no2).
3. Predictions include horizon-scaled adjustments and 95% confidence intervals.
4. Feature importance extracted via built-in XGBoost gain scores.

## Troubleshooting

### App starts but page looks old

1. Hard refresh browser (Ctrl+Shift+R).
2. Restart Streamlit.

### Map does not reflect expected risk

1. Change sidebar controls and confirm metric cards update.
2. Ensure selected city matches what you are presenting.

### API fetch returns synthetic data

1. Check `.env` file has valid API keys.
2. Free tier rate limits may apply — cached data (15 min TTL) is used when available.

## Repository Files

1. app.py - main dashboard app.
2. requirements.txt - Python dependencies.
3. env.example - sample environment variable template.
4. .gitignore - local/secret file ignores.
