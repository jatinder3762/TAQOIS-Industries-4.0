# TAQOIS Industries 4.0 - Air Quality Command Dashboard

Professional Streamlit command-and-control dashboard for corridor-level air quality risk simulation with 3D geospatial visualization and Gemini-assisted operational intelligence.

## What This App Does

The dashboard simulates air-quality pressure across key traffic and industrial corridors and converts that into actionable operations views:

1. City-level status and hotspot counts.
2. 3D map for quick spatial risk scanning.
3. Corridor matrix with PM2.5, NO2, and exposure estimates.
4. AI-generated executive and response content (when Gemini key is available).

## Current Scope

This version is simulation-based for operational prototyping.

1. Data shown is synthetic (model-driven), not live regulatory feed yet.
2. City switcher is available in the sidebar.
3. Login page is planned for a future upgrade.

## Features

### 1. Simulation Controls

Sidebar controls:

1. City
2. Traffic Volume
3. Weather Inversion
4. Industrial Activity
5. Wind Speed
6. Humidity
7. Special Event / Incident Surge

These inputs dynamically recalculate corridor risk and update all visuals in real time.

### 2. 3D Corridor Map (PyDeck)

Map interpretation:

1. Dot: corridor location.
2. 3D column height: risk intensity.
3. Column color:
   - Green: Low
   - Cyan: Elevated
   - Amber: High
   - Red: Severe
4. Hover tooltip shows corridor name, risk score, PM2.5, and NO2.

### 3. Threat Matrix

Each row is a corridor with:

1. Risk (0 to 100): higher means more pressure.
2. PM2.5: estimated fine particulate level.
3. NO2: estimated nitrogen dioxide level.
4. Exposure: combined estimate weighted by population pressure.

### 4. Gemini 2.5 Flash Integration

When GEMINI_API_KEY is available, the app generates:

1. Executive Briefing
2. Tactical Response Plan
3. Public Health Advisory

If Gemini is unavailable, the app automatically falls back to deterministic local text.

## Tech Stack

1. Python 3.10+
2. Streamlit
3. Pandas
4. PyDeck
5. google-generativeai
6. python-dotenv

## Local Setup (VS Code Terminal)

### 1. Create and activate virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure Gemini key

Create a .env file in project root:

```env
GEMINI_API_KEY=your_real_key_here
```

Important behavior:

1. The app loads .env automatically.
2. Existing environment variables are not overridden by .env values.

### 4. Run the app

```powershell
streamlit run app.py
```

## How To Use (Zero-Knowledge Walkthrough)

Use this sequence during demos:

1. Select a city from the sidebar.
2. Move Traffic, Weather Inversion, and Industrial sliders.
3. Show city status cards changing instantly.
4. Explain map quickly:
   - Dot = where
   - Height = how bad
   - Color = severity
5. Hover columns to show PM2.5 and NO2 details.
6. Open AI tabs and read generated actions/advisories.

## How The Model Works (Simple)

For each corridor, the engine combines:

1. Emissions pressure drivers: traffic, inversion, industrial load.
2. Weather modifiers: wind and humidity.
3. Corridor sensitivity and population index.

Then it outputs:

1. Risk score (0 to 100)
2. Risk level band
3. Estimated PM2.5 and NO2
4. Exposure index

## Insights To Communicate Clearly

When presenting, keep language simple:

1. Citywide Status: overall pressure level right now.
2. Critical Hotspots: count of corridors in severe band.
3. Peak Corridor Risk: worst location currently.
4. Primary Drivers: major causes from the simulation settings.

## Troubleshooting

### App starts but page looks old

1. Hard refresh browser.
2. Restart Streamlit.

### Gemini content is not changing

1. Confirm key exists in .env.
2. Restart Streamlit after updating .env.
3. Verify internet connectivity.

### Map does not reflect expected risk

1. Change sidebar controls and confirm metric cards update.
2. Ensure selected city is the one you are presenting.

## Known Warnings

1. google-generativeai shows a deprecation warning upstream; app still runs.
2. Streamlit warns about future use_container_width changes; non-blocking.

## Roadmap

Planned next upgrades:

1. Live Canadian air-quality data integration.
2. Login/authentication before dashboard access.
3. Data source status badge and model confidence indicators.

## Repository Files

1. app.py - main dashboard app.
2. requirements.txt - Python dependencies.
3. env.example - sample environment variable template.
4. .gitignore - local/secret file ignores.
