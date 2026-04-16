import os
import random
from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd
import pydeck as pdk
import streamlit as st
from dotenv import load_dotenv

from data_ingestion import fetch_corridor_conditions, conditions_to_sim_inputs
from forecast_engine import get_forecast_model, FEATURE_COLS
from database import (
    init_db,
    store_predictions,
    store_action,
    get_recent_predictions,
    get_recent_actions,
    get_audit_log,
    log_event,
    prediction_count_by_day,
)


load_dotenv(override=False)
init_db()


st.set_page_config(
    page_title="TAQOIS Command & Control",
    page_icon="AQ",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --bg: #060c14;
    --panel: linear-gradient(160deg, rgba(12, 20, 33, 0.82), rgba(16, 26, 42, 0.72));
    --panel-2: linear-gradient(145deg, rgba(13, 23, 39, 0.94), rgba(18, 30, 49, 0.82));
    --text: #e6f0fa;
    --muted: #9bb1c6;
    --cyan: #43c8e6;
    --cyan-soft: #8ed8ea;
    --pink: #9ea6ff;
    --green: #66d0a2;
    --amber: #f2bd6d;
    --red: #df7c8d;
    --border: rgba(67, 200, 230, 0.22);
    --panel-border: rgba(146, 171, 196, 0.20);
    --shadow: 0 12px 26px rgba(2, 8, 18, 0.60), 0 0 18px rgba(67, 200, 230, 0.06);
}
html, body, [data-testid="stAppViewContainer"] {
  background:
        radial-gradient(circle at 12% 14%, rgba(67,200,230,0.10), transparent 26%),
        radial-gradient(circle at 86% 18%, rgba(158,166,255,0.07), transparent 22%),
        radial-gradient(circle at 48% 84%, rgba(102,208,162,0.06), transparent 24%),
        linear-gradient(140deg, #03070d 0%, #060c14 44%, #0a1627 100%);
  color: var(--text);
    font-family: "Space Grotesk", "Segoe UI", sans-serif;
}

[data-testid="stHeader"] {
    background: transparent !important;
}

[data-testid="stToolbar"] {
    right: 0.75rem;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(6, 13, 24, 0.96), rgba(6, 13, 24, 0.90));
    border-right: 1px solid rgba(67,200,230,0.14);
}
.block-container {
    padding-top: 1.6rem;
    padding-bottom: 1.6rem;
}

.block-container::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background-image:
        linear-gradient(rgba(142,216,234,0.024) 1px, transparent 1px),
        linear-gradient(90deg, rgba(142,216,234,0.024) 1px, transparent 1px);
    background-size: 42px 42px;
    mask-image: radial-gradient(circle at 50% 50%, rgba(0,0,0,0.9) 38%, transparent 78%);
}

.glass {
    background: var(--panel);
    border: 1px solid var(--panel-border);
  box-shadow: var(--shadow);
    backdrop-filter: blur(14px);
    border-radius: 20px;
    padding: 16px 18px;
}
.hero {
    position: relative;
    background: linear-gradient(136deg, rgba(67,200,230,0.10), rgba(158,166,255,0.06));
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 20px 24px;
    box-shadow: var(--shadow);
    margin-bottom: 16px;
    overflow: hidden;
}

.hero::after {
    content: "";
    position: absolute;
    right: -70px;
    top: -70px;
    width: 220px;
    height: 220px;
    background: radial-gradient(circle, rgba(67,200,230,0.20), rgba(67,200,230,0) 70%);
}

.hero-title {
    font-family: "Orbitron", "Space Grotesk", sans-serif;
    letter-spacing: 0.03em;
}

.hero-subtitle {
    max-width: 860px;
    color: #b8d9ee;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
    gap: 14px;
}
.metric-card {
  background: var(--panel-2);
  border: 1px solid var(--border);
    border-radius: 16px;
    padding: 15px 16px;
    min-height: 102px;
  box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.metric-card:hover {
    border-color: rgba(142, 216, 234, 0.44);
    box-shadow: 0 14px 26px rgba(2, 8, 18, 0.66), 0 0 24px rgba(67, 200, 230, 0.10);
}

.metric-card::before {
    content: "";
    position: absolute;
    left: -35px;
    top: -40px;
    width: 130px;
    height: 130px;
    background: radial-gradient(circle, rgba(67,200,230,0.12), rgba(67,200,230,0));
}

.metric-label {
    color: var(--muted);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 4px;
}

.metric-value {
    font-size: 1.72rem;
    font-weight: 700;
    color: var(--text);
    line-height: 1.16;
}

.metric-delta {
    font-size: 0.82rem;
    color: #b7cadc;
    margin-top: 2px;
}

.alert-chip {
  display: inline-block;
    padding: 5px 11px;
  border-radius: 999px;
    font-weight: 600;
    font-size: 0.8rem;
  margin-right: 8px;
    border: 1px solid rgba(255,255,255,0.16);
        transition: background-color 0.2s ease, border-color 0.2s ease;
}

.alert-chip:hover {
        border-color: rgba(210, 224, 235, 0.40);
}

.section-title {
    font-family: "Orbitron", "Space Grotesk", sans-serif;
    letter-spacing: 0.04em;
    font-size: 0.92rem;
    text-transform: uppercase;
    color: #a8bfd5;
}

.footer-note { color: var(--muted); font-size: 0.85rem; }
h1, h2, h3 { color: var(--text); }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] {
    background: rgba(255,255,255,0.04);
  border-radius: 12px;
  padding: 10px 14px;
    border: 1px solid rgba(67,200,230,0.14);
}

.stTabs [data-baseweb="tab"]:hover {
    background: rgba(142, 216, 234, 0.10);
    border-color: rgba(142, 216, 234, 0.34);
}

.stTabs [aria-selected="true"] {
    background: rgba(67, 200, 230, 0.12) !important;
    border-color: rgba(142, 216, 234, 0.40) !important;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] label,
[data-testid="stCaptionContainer"] {
    color: #d4e2f0;
    line-height: 1.55;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #b9cde0;
}

[data-testid="stDataFrame"] {
    border: 1px solid rgba(67,200,230,0.14);
    border-radius: 14px;
}

/* Expander */
[data-testid="stExpander"] {
    background: var(--panel-2);
    border: 1px solid var(--border);
    border-radius: 14px;
}
[data-testid="stExpander"] summary {
    color: var(--cyan-soft) !important;
}
[data-testid="stExpander"] summary:hover {
    color: var(--cyan) !important;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    background: transparent;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, rgba(67,200,230,0.18), rgba(158,166,255,0.12));
    color: var(--cyan-soft) !important;
    border: 1px solid var(--border);
    border-radius: 12px;
    font-weight: 600;
    transition: all 0.25s ease;
}
.stButton > button:hover {
    background: linear-gradient(135deg, rgba(67,200,230,0.32), rgba(158,166,255,0.22));
    border-color: rgba(142, 216, 234, 0.50);
    color: #fff !important;
    box-shadow: 0 0 18px rgba(67, 200, 230, 0.18);
}
.stButton > button:active,
.stButton > button:focus {
    background: linear-gradient(135deg, rgba(67,200,230,0.28), rgba(158,166,255,0.18));
    color: #fff !important;
    border-color: rgba(142, 216, 234, 0.44);
}

/* Radio buttons & toggles */
[data-testid="stRadio"] label:hover {
    color: var(--cyan) !important;
}
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: var(--cyan) !important;
    border-color: var(--cyan) !important;
}
.stSlider [data-baseweb="slider"] [role="slider"]:hover {
    box-shadow: 0 0 10px rgba(67, 200, 230, 0.40);
}

/* Selectbox & inputs */
[data-baseweb="select"] > div {
    background: rgba(10, 18, 30, 0.80) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}
[data-baseweb="select"] > div:hover {
    border-color: rgba(142, 216, 234, 0.40) !important;
}
[data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="select"] [role="listbox"] {
    background: rgba(12, 20, 33, 0.96) !important;
    border: 1px solid var(--border) !important;
}
[data-baseweb="select"] [role="option"] {
    color: var(--text) !important;
}
[data-baseweb="select"] [role="option"]:hover {
    background: rgba(67, 200, 230, 0.14) !important;
}

/* Toggle */
[data-testid="stToggle"] label span {
    color: var(--muted) !important;
}

/* Metric cards (Streamlit native) */
[data-testid="stMetric"] {
    background: var(--panel-2);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 12px 14px;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(142, 216, 234, 0.44);
    box-shadow: 0 0 16px rgba(67, 200, 230, 0.10);
}
[data-testid="stMetricLabel"] {
    color: var(--muted) !important;
}
[data-testid="stMetricValue"] {
    color: var(--text) !important;
}

/* Spinner */
.stSpinner > div {
    border-top-color: var(--cyan) !important;
}

/* Success / warning / error / info alerts */
[data-testid="stAlert"] {
    background: rgba(12, 20, 33, 0.80) !important;
    border-radius: 12px;
}

@media (max-width: 1200px) {
    .metric-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 760px) {
    .metric-grid {
        grid-template-columns: 1fr;
    }
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

CORRIDORS = [
    {
        "name": "Highway 401 / Allen Road",
        "lat": 43.7328,
        "lon": -79.4584,
        "population_index": 0.92,
        "sensitivity": 1.18,
        "baseline_pm25": 15.0,
        "baseline_no2": 34.0,
    },
    {
        "name": "Gardiner Expressway / Spadina",
        "lat": 43.6407,
        "lon": -79.3992,
        "population_index": 0.89,
        "sensitivity": 1.14,
        "baseline_pm25": 14.0,
        "baseline_no2": 31.0,
    },
    {
        "name": "DVP / Don Mills Corridor",
        "lat": 43.7137,
        "lon": -79.3468,
        "population_index": 0.84,
        "sensitivity": 1.11,
        "baseline_pm25": 13.5,
        "baseline_no2": 30.0,
    },
    {
        "name": "Lake Shore West / Humber Bay",
        "lat": 43.6243,
        "lon": -79.4878,
        "population_index": 0.76,
        "sensitivity": 1.06,
        "baseline_pm25": 12.5,
        "baseline_no2": 26.0,
    },
    {
        "name": "Scarborough Industrial Belt",
        "lat": 43.7820,
        "lon": -79.2485,
        "population_index": 0.81,
        "sensitivity": 1.16,
        "baseline_pm25": 16.0,
        "baseline_no2": 29.0,
    },
    {
        "name": "Etobicoke South Industrial Zone",
        "lat": 43.6187,
        "lon": -79.5301,
        "population_index": 0.74,
        "sensitivity": 1.10,
        "baseline_pm25": 15.2,
        "baseline_no2": 27.5,
    },
    {
        "name": "Yonge / Finch Corridor",
        "lat": 43.7809,
        "lon": -79.4149,
        "population_index": 0.87,
        "sensitivity": 1.12,
        "baseline_pm25": 13.8,
        "baseline_no2": 29.5,
    },
    {
        "name": "Queen / King Streetcar Belt",
        "lat": 43.6505,
        "lon": -79.3783,
        "population_index": 0.94,
        "sensitivity": 1.09,
        "baseline_pm25": 12.9,
        "baseline_no2": 28.4,
    },
    {
        "name": "Keele / Junction Industrial",
        "lat": 43.6656,
        "lon": -79.4630,
        "population_index": 0.78,
        "sensitivity": 1.15,
        "baseline_pm25": 14.6,
        "baseline_no2": 27.8,
    },
    {
        "name": "Eglinton Crosstown Corridor",
        "lat": 43.7070,
        "lon": -79.3980,
        "population_index": 0.86,
        "sensitivity": 1.08,
        "baseline_pm25": 13.1,
        "baseline_no2": 28.0,
    },
    {
        "name": "Dundas / Ossington Residential",
        "lat": 43.6510,
        "lon": -79.4220,
        "population_index": 0.90,
        "sensitivity": 1.05,
        "baseline_pm25": 11.8,
        "baseline_no2": 25.6,
    },
    {
        "name": "Steeles / Markham Gateway",
        "lat": 43.8010,
        "lon": -79.3280,
        "population_index": 0.77,
        "sensitivity": 1.13,
        "baseline_pm25": 14.2,
        "baseline_no2": 30.1,
    },
    {
        "name": "Bloor / Danforth Transit Line",
        "lat": 43.6710,
        "lon": -79.3260,
        "population_index": 0.88,
        "sensitivity": 1.07,
        "baseline_pm25": 12.4,
        "baseline_no2": 26.9,
    },
    {
        "name": "Weston / 401 Industrial Node",
        "lat": 43.7060,
        "lon": -79.5150,
        "population_index": 0.73,
        "sensitivity": 1.17,
        "baseline_pm25": 15.5,
        "baseline_no2": 31.2,
    },
    {
        "name": "Waterfront / Port Lands",
        "lat": 43.6390,
        "lon": -79.3490,
        "population_index": 0.80,
        "sensitivity": 1.10,
        "baseline_pm25": 13.3,
        "baseline_no2": 27.2,
    },
]

CITY_PRESETS = {
    "Toronto": {
        "center": {"lat": 43.70011, "lon": -79.4163, "zoom": 10},
        "corridors": CORRIDORS,
    },
    "Vancouver": {
        "center": {"lat": 49.2827, "lon": -123.1207, "zoom": 10},
        "corridors": [
            {
                "name": "Broadway / Cambie",
                "lat": 49.2625,
                "lon": -123.1149,
                "population_index": 0.88,
                "sensitivity": 1.12,
                "baseline_pm25": 11.8,
                "baseline_no2": 24.0,
            },
            {
                "name": "Georgia / Denman",
                "lat": 49.2925,
                "lon": -123.1320,
                "population_index": 0.82,
                "sensitivity": 1.07,
                "baseline_pm25": 10.9,
                "baseline_no2": 22.6,
            },
            {
                "name": "Knight Street Bridge Access",
                "lat": 49.2108,
                "lon": -123.0771,
                "population_index": 0.79,
                "sensitivity": 1.10,
                "baseline_pm25": 12.2,
                "baseline_no2": 25.3,
            },
            {
                "name": "Hastings Industrial Interface",
                "lat": 49.2818,
                "lon": -123.0411,
                "population_index": 0.76,
                "sensitivity": 1.15,
                "baseline_pm25": 12.6,
                "baseline_no2": 26.2,
            },
            {
                "name": "Marine Drive / Oak",
                "lat": 49.2088,
                "lon": -123.1280,
                "population_index": 0.74,
                "sensitivity": 1.08,
                "baseline_pm25": 11.4,
                "baseline_no2": 23.5,
            },
            {
                "name": "Port Access / Powell",
                "lat": 49.2863,
                "lon": -123.0616,
                "population_index": 0.80,
                "sensitivity": 1.14,
                "baseline_pm25": 12.9,
                "baseline_no2": 27.1,
            },
        ],
    },
    "Montreal": {
        "center": {"lat": 45.5017, "lon": -73.5673, "zoom": 10},
        "corridors": [
            {
                "name": "Autoroute 40 / Decarie",
                "lat": 45.5047,
                "lon": -73.6902,
                "population_index": 0.90,
                "sensitivity": 1.16,
                "baseline_pm25": 13.7,
                "baseline_no2": 30.3,
            },
            {
                "name": "Ville-Marie / Berri",
                "lat": 45.5139,
                "lon": -73.5586,
                "population_index": 0.86,
                "sensitivity": 1.10,
                "baseline_pm25": 12.8,
                "baseline_no2": 27.8,
            },
            {
                "name": "Jacques-Cartier Approach",
                "lat": 45.5490,
                "lon": -73.5344,
                "population_index": 0.79,
                "sensitivity": 1.07,
                "baseline_pm25": 12.2,
                "baseline_no2": 25.6,
            },
            {
                "name": "Mercier Industrial Axis",
                "lat": 45.5775,
                "lon": -73.5474,
                "population_index": 0.77,
                "sensitivity": 1.14,
                "baseline_pm25": 13.9,
                "baseline_no2": 28.1,
            },
            {
                "name": "Champlain / Nuns' Island",
                "lat": 45.4651,
                "lon": -73.5475,
                "population_index": 0.74,
                "sensitivity": 1.06,
                "baseline_pm25": 11.9,
                "baseline_no2": 24.9,
            },
            {
                "name": "Pie-IX / Olympic Sector",
                "lat": 45.5588,
                "lon": -73.5522,
                "population_index": 0.82,
                "sensitivity": 1.11,
                "baseline_pm25": 12.7,
                "baseline_no2": 26.4,
            },
        ],
    },
}

SCENARIOS = {
    "Normal Operations": {
        "description": "Baseline conditions. Air quality is within safe range across all corridors.",
        "icon": "[NORMAL]",
        "traffic_volume": 45,
        "inversion_strength": 20,
        "industrial_activity": 35,
        "wind_speed": 28,
        "humidity": 48,
        "emergency_event": False,
        "iot_overrides": {},
    },
    "Wildfire / Smoke Event": {
        "description": "Regional wildfire drives a PM2.5 surge across downwind corridors.",
        "icon": "[WILDFIRE]",
        "traffic_volume": 55,
        "inversion_strength": 82,
        "industrial_activity": 40,
        "wind_speed": 8,
        "humidity": 28,
        "emergency_event": True,
        "iot_overrides": {"PM2.5 Spike": "+340%", "Visibility": "Low", "AQI": "Hazardous"},
    },
    "Severe Temperature Inversion": {
        "description": "Warm air traps ground-level pollutants - emissions cannot disperse.",
        "icon": "[INVERSION]",
        "traffic_volume": 70,
        "inversion_strength": 95,
        "industrial_activity": 65,
        "wind_speed": 4,
        "humidity": 82,
        "emergency_event": False,
        "iot_overrides": {"NO2": "+180%", "CO": "Elevated", "AQI": "Very Unhealthy"},
    },
    "Industrial Incident": {
        "description": "Unplanned emissions release from industrial zone - localized severe impact.",
        "icon": "[INDUSTRIAL]",
        "traffic_volume": 60,
        "inversion_strength": 58,
        "industrial_activity": 98,
        "wind_speed": 12,
        "humidity": 56,
        "emergency_event": True,
        "iot_overrides": {"SO2": "Critical", "PM10": "+220%", "AQI": "Hazardous"},
    },
    "Rush Hour + Heatwave": {
        "description": "Peak traffic combined with extreme heat intensifies ground-level ozone.",
        "icon": "[HEATWAVE]",
        "traffic_volume": 95,
        "inversion_strength": 75,
        "industrial_activity": 60,
        "wind_speed": 6,
        "humidity": 78,
        "emergency_event": False,
        "iot_overrides": {"Ozone": "+160%", "Temperature": "38 C", "AQI": "Unhealthy"},
    },
}

RISK_BANDS = [
    (0, 24, "LOW", "#57ff9a"),
    (25, 49, "ELEVATED", "#2ef2ff"),
    (50, 74, "HIGH", "#ffc857"),
    (75, 100, "SEVERE", "#ff5e7e"),
]


@dataclass
class SimulationInputs:
    traffic_volume: int
    inversion_strength: int
    industrial_activity: int
    wind_speed: int
    humidity: int
    emergency_event: bool


class SimulationEngine:
    def __init__(self, corridors: List[Dict]):
        self.corridors = corridors

    def run(self, sim: SimulationInputs) -> pd.DataFrame:
        rows = []
        for idx, c in enumerate(self.corridors):
            traffic_factor = (sim.traffic_volume / 100) * (1.05 + idx * 0.015)
            inversion_factor = (sim.inversion_strength / 100) * 1.25
            industrial_factor = (sim.industrial_activity / 100) * (1.0 + (0.12 if "Industrial" in c["name"] else 0.0))
            weather_relief = max(0.35, 1 - (sim.wind_speed / 160))
            humidity_penalty = sim.humidity / 250
            emergency_penalty = 0.18 if sim.emergency_event else 0.0

            raw_score = (
                22 * traffic_factor
                + 27 * inversion_factor
                + 18 * industrial_factor
                + 16 * c["population_index"]
                + 10 * humidity_penalty
                + 7 * emergency_penalty
            ) * c["sensitivity"] * weather_relief

            risk_score = max(0, min(100, round(raw_score, 1)))
            pm25 = round(c["baseline_pm25"] + risk_score * 0.23, 1)
            no2 = round(c["baseline_no2"] + risk_score * 0.31, 1)
            exposure = round((pm25 * 0.55 + no2 * 0.45) * c["population_index"], 1)
            level, color = self._risk_level(risk_score)

            rows.append(
                {
                    "corridor": c["name"],
                    "lat": c["lat"],
                    "lon": c["lon"],
                    "risk_score": risk_score,
                    "risk_level": level,
                    "color": color,
                    "color_rgba": [int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16), 210],
                    "pm25_est": pm25,
                    "no2_est": no2,
                    "population_index": c["population_index"],
                    "exposure_index": exposure,
                    "elevation": risk_score * 120,
                    "radius": 380 + risk_score * 10,
                }
            )
        df = pd.DataFrame(rows).sort_values("risk_score", ascending=False).reset_index(drop=True)
        return df

    def _risk_level(self, score: float):
        for low, high, label, color in RISK_BANDS:
            if low <= score <= high:
                return label, color
        return "UNKNOWN", "#ffffff"


def generate_intel(payload: Dict) -> Dict[str, str]:
    city = payload.get("city", "the selected city")
    top = payload["top_corridors"]
    avg = payload["avg_risk"]
    max_risk = payload.get("max_risk", avg)
    urgency = payload["citywide_status"]
    drivers = payload.get("drivers", {})

    # Adaptive driver analysis
    driver_ranking = sorted(
        [
            ("traffic congestion", drivers.get("traffic_volume", 0)),
            ("atmospheric inversion", drivers.get("weather_inversion", 0)),
            ("industrial emissions", drivers.get("industrial_activity", 0)),
        ],
        key=lambda x: x[1],
        reverse=True,
    )
    top_driver = driver_ranking[0][0]
    wind = drivers.get("wind_speed", 15)
    humidity = drivers.get("humidity", 50)
    emergency = drivers.get("special_event", False)

    # Context-sensitive recommendations
    response_actions = []
    if drivers.get("traffic_volume", 0) >= 70:
        response_actions.append(
            "Deploy traffic-flow optimization on the top-three affected corridors; "
            "coordinate with Transportation Services for signal timing adjustments."
        )
    if drivers.get("weather_inversion", 0) >= 60:
        response_actions.append(
            "Inversion trapping detected — advise Toronto Public Health to prepare "
            "sensitive-population alerts. Emissions cannot disperse effectively."
        )
    if drivers.get("industrial_activity", 0) >= 65:
        response_actions.append(
            "Coordinate with industrial compliance partners to defer discretionary "
            "emissions in the Scarborough and Etobicoke zones."
        )
    if wind < 10:
        response_actions.append(
            "Wind speed critically low — pollutant dispersion is impaired. "
            "Increase monitoring frequency to every 15 minutes."
        )
    if emergency:
        response_actions.append(
            "Emergency event active — escalate to Toronto Emergency Management. "
            "Consider activating the smoke/heat coordination protocol."
        )
    if avg >= 75:
        response_actions.append(
            "SEVERE threshold crossed — recommend immediate coordination call "
            "between Public Health, Transportation, and Emergency Management."
        )
    if not response_actions:
        response_actions.append(
            "Conditions within normal range. Maintain standard monitoring cadence."
        )

    numbered_actions = "\n".join(f"{i+1}. {a}" for i, a in enumerate(response_actions))

    # Forecast-aware briefing
    forecast_note = ""
    if avg >= 50:
        forecast_note = (
            f" Forecasting models project continued elevated risk over the next 2-4 hours "
            f"unless {top_driver} pressure subsides. Re-assessment recommended at 30-minute intervals."
        )

    return {
        "executive_briefing": (
            f"{city} air-quality intelligence indicates a **{urgency}** citywide posture "
            f"with an average corridor risk of **{avg}** and peak risk of **{max_risk}**. "
            f"The primary stress driver is **{top_driver}** "
            f"(wind: {wind} km/h, humidity: {humidity}%). "
            f"Priority corridors: **{top[0]}**, **{top[1]}**, and **{top[2]}**."
            f"{forecast_note}"
        ),
        "tactical_response_plan": numbered_actions,
        "public_health_advisory": (
            f"Air quality is currently under **{urgency.lower()}** pressure in parts of {city}, "
            f"concentrated near **{top[0]}**, **{top[1]}**, and **{top[2]}**. "
            f"The dominant factor is {top_driver}. "
            "Children, older adults, and individuals with respiratory or cardiovascular "
            "conditions should limit outdoor exertion near major corridors. "
            "Keep windows closed and use air filtration where available. "
            f"{'An emergency event is active — follow municipal emergency guidance.' if emergency else 'Monitor city advisories for updates.'}"
        ),
    }


def city_status(avg_risk: float) -> str:
    if avg_risk >= 75:
        return "SEVERE"
    if avg_risk >= 50:
        return "HIGH"
    if avg_risk >= 25:
        return "ELEVATED"
    return "LOW"


@dataclass
class ScenarioRuntime:
    frame: int = 0
    running: bool = False
    history: List[Dict] = field(default_factory=list)
    advisories: List[Dict] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    phase: str = ""


class ScenarioSimulationController:
    TOTAL_FRAMES = 48
    ANIM_PHASES = [
        (0, 9, "Normal Conditions", "#57ff9a", 0.00),
        (10, 19, "Event Building", "#2ef2ff", 0.42),
        (20, 29, "Peak Intensity", "#ffc857", 0.92),
        (30, 39, "Sustained Impact", "#f2bd6d", 0.74),
        (40, 48, "Recovery", "#57ff9a", 0.22),
    ]

    def __init__(self, city_config: Dict, selected_city: str, selected_scenario: str, scenario_cfg: Dict):
        self.city_config = city_config
        self.selected_city = selected_city
        self.selected_scenario = selected_scenario
        self.scenario_cfg = scenario_cfg
        self.engine = SimulationEngine(city_config["corridors"])

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    @staticmethod
    def _risk_to_rgba(risk: float) -> List[int]:
        # Smooth gradient: green -> yellow -> orange -> red
        stops = [
            (0.0, (87, 255, 154)),
            (40.0, (255, 221, 87)),
            (70.0, (255, 163, 72)),
            (100.0, (255, 94, 126)),
        ]
        clamped = max(0.0, min(100.0, float(risk)))
        for i in range(len(stops) - 1):
            left_risk, left_color = stops[i]
            right_risk, right_color = stops[i + 1]
            if left_risk <= clamped <= right_risk:
                t = (clamped - left_risk) / (right_risk - left_risk)
                r = int(left_color[0] + (right_color[0] - left_color[0]) * t)
                g = int(left_color[1] + (right_color[1] - left_color[1]) * t)
                b = int(left_color[2] + (right_color[2] - left_color[2]) * t)
                return [r, g, b, 220]
        return [255, 94, 126, 220]

    def phase_for_frame(self, frame: int):
        for start, end, label, color, intensity in self.ANIM_PHASES:
            if start <= frame <= end:
                return label, color, intensity
        return "Recovery", "#57ff9a", 0.22

    def ensure_state(self, reset_token: str) -> ScenarioRuntime:
        if st.session_state.get("scenario_reset_token") != reset_token:
            st.session_state.scenario_reset_token = reset_token
            st.session_state.scen_frame = 0
            st.session_state.scen_running = False
            st.session_state.scen_history = []
            st.session_state.scen_advisories = []
            st.session_state.scen_logs = ["[INIT] Scenario reset and ready for re-run."]
            st.session_state.scen_phase = ""
        return ScenarioRuntime(
            frame=st.session_state.scen_frame,
            running=st.session_state.scen_running,
            history=st.session_state.scen_history,
            advisories=st.session_state.scen_advisories,
            logs=st.session_state.scen_logs,
            phase=st.session_state.scen_phase,
        )

    def add_log(self, message: str) -> None:
        logs = st.session_state.scen_logs
        logs.append(message)
        st.session_state.scen_logs = logs[-18:]

    def compute_frame(self, frame: int):
        phase_label, phase_color, intensity = self.phase_for_frame(frame)
        sim = SimulationInputs(
            traffic_volume=round(self._lerp(45, self.scenario_cfg["traffic_volume"], intensity)),
            inversion_strength=round(self._lerp(20, self.scenario_cfg["inversion_strength"], intensity)),
            industrial_activity=round(self._lerp(35, self.scenario_cfg["industrial_activity"], intensity)),
            wind_speed=round(self._lerp(28, self.scenario_cfg["wind_speed"], intensity)),
            humidity=round(self._lerp(48, self.scenario_cfg["humidity"], intensity)),
            emergency_event=(intensity >= 0.65 and self.scenario_cfg["emergency_event"]),
        )
        df = self.engine.run(sim)
        df["sim_color_rgba"] = df["risk_score"].apply(self._risk_to_rgba)
        avg_risk = round(df["risk_score"].mean(), 1)
        max_pm25 = round(df["pm25_est"].max(), 1)
        avg_no2 = round(df["no2_est"].mean(), 1)
        return df, avg_risk, max_pm25, avg_no2, sim, phase_label, phase_color


        max_pm25 = round(df["pm25_est"].max(), 1)
        avg_no2 = round(df["no2_est"].mean(), 1)
        return df, avg_risk, max_pm25, avg_no2, sim, phase_label, phase_color


# ======================================================================
# FORECAST PAGE
# ======================================================================

def render_forecast_page(city_config: dict, selected_city: str, controls) -> None:  # noqa: C901
    import plotly.graph_objects as go
    from datetime import datetime, timezone

    st.markdown(
        """
        <div class="hero">
          <div>
            <div style="font-size:0.85rem; color:#8bb8c8; letter-spacing:0.12em; text-transform:uppercase;">AI Forecasting Engine</div>
            <h1 class="hero-title" style="margin:0.2rem 0 0.35rem 0;">Short-Horizon Air Quality Forecast</h1>
            <div class="hero-subtitle">XGBoost-powered predictions for 2, 4, and 6-hour horizons across all monitored corridors. Includes confidence intervals and model explainability.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    corridors = city_config["corridors"]
    model = get_forecast_model()

    # Train model if needed
    if not model.trained:
        with st.spinner("Training XGBoost forecasting model on corridor data..."):
            metrics = model.train(corridors)
            log_event("model_trained", metrics)
        st.success(
            f"Model trained — RMSE: risk={metrics['risk_score_rmse']}, "
            f"PM2.5={metrics['pm25_rmse']}, NO2={metrics['no2_rmse']}"
        )

    # Fetch live conditions
    st.markdown('<div class="section-title">Live Data Ingestion</div>', unsafe_allow_html=True)

    with st.expander("Fetch real-time conditions from APIs", expanded=False):
        if st.button("Fetch Live Weather & AQ Data", key="fetch_live"):
            with st.spinner("Querying OpenWeatherMap & AQICN APIs..."):
                live_data = fetch_corridor_conditions(corridors)
                st.session_state["live_conditions"] = live_data
                log_event("live_data_fetched", {"city": selected_city, "corridors": len(live_data)})
            st.success(f"Fetched data for {len(live_data)} corridors.")

        if st.session_state.get("live_conditions"):
            live = st.session_state["live_conditions"]
            live_summary = []
            for item in live:
                w = item["weather"]
                aq = item["air_quality"]
                live_summary.append({
                    "Corridor": item["corridor"],
                    "Temp (°C)": w.get("temperature_c"),
                    "Wind (km/h)": w.get("wind_speed_kmh"),
                    "Humidity (%)": w.get("humidity"),
                    "AQI": aq.get("aqi"),
                    "PM2.5": aq.get("pm25"),
                    "NO2": aq.get("no2"),
                    "Source": w.get("source", ""),
                })
            st.dataframe(pd.DataFrame(live_summary), use_container_width=True, hide_index=True)

    # Build conditions from sidebar sliders (or live data if available)
    conditions = {
        "traffic_volume": controls.traffic_volume,
        "inversion_strength": controls.inversion_strength,
        "industrial_activity": controls.industrial_activity,
        "wind_speed": controls.wind_speed,
        "humidity": controls.humidity,
        "temperature_c": 20,
        "emergency_event": int(controls.emergency_event),
    }

    if st.session_state.get("live_conditions"):
        first_weather = st.session_state["live_conditions"][0]["weather"]
        live_sim = conditions_to_sim_inputs(first_weather)
        conditions["wind_speed"] = live_sim["wind_speed"]
        conditions["humidity"] = live_sim["humidity"]
        conditions["inversion_strength"] = live_sim["inversion_strength"]
        conditions["temperature_c"] = live_sim["temperature_c"]

    # Run forecast
    st.markdown('<div class="section-title">Corridor Forecast (2-6 Hour Horizon)</div>', unsafe_allow_html=True)

    forecasts = model.predict(corridors, conditions, horizons_hours=[2, 4, 6])

    # Store predictions in database
    store_predictions(selected_city, forecasts, conditions)

    # Horizon selector
    horizon = st.radio("Forecast horizon", [2, 4, 6], horizontal=True, format_func=lambda h: f"{h}-Hour")
    df_h = forecasts[forecasts["horizon_hours"] == horizon].copy()
    df_h = df_h.sort_values("risk_score", ascending=False).reset_index(drop=True)

    # Metrics row
    avg_risk = round(df_h["risk_score"].mean(), 1)
    max_pm25 = round(df_h["pm25"].max(), 1)
    hotspots = int((df_h["risk_score"] >= 75).sum())
    status = city_status(avg_risk)

    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card"><div class="metric-label">Predicted Status ({horizon}h)</div><div class="metric-value">{status}</div><div class="metric-delta">Avg risk {avg_risk}</div></div>
            <div class="metric-card"><div class="metric-label">Predicted Hotspots</div><div class="metric-value">{hotspots}</div><div class="metric-delta">Corridors expected at SEVERE</div></div>
            <div class="metric-card"><div class="metric-label">Peak PM2.5 Forecast</div><div class="metric-value">{max_pm25}</div><div class="metric-delta">Highest corridor estimate</div></div>
            <div class="metric-card"><div class="metric-label">Avg Confidence</div><div class="metric-value">{round(df_h['risk_score_confidence'].mean() * 100, 1)}%</div><div class="metric-delta">Model certainty</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Forecast table and map
    fc1, fc2 = st.columns([1.35, 1])
    with fc1:
        st.markdown('<div class="section-title">Forecast Map</div>', unsafe_allow_html=True)

        df_h["elevation"] = df_h["risk_score"] * 120
        df_h["radius"] = 380 + df_h["risk_score"] * 10
        df_h["color_rgba"] = df_h["risk_score"].apply(
            lambda s: [
                int(min(255, 87 + (s / 100) * 168)),
                int(max(94, 255 - (s / 100) * 161)),
                int(max(126, 154 - (s / 50) * 28)),
                210,
            ]
        )

        deck = pdk.Deck(
            map_style="dark",
            initial_view_state=pdk.ViewState(
                latitude=city_config["center"]["lat"],
                longitude=city_config["center"]["lon"],
                zoom=city_config["center"]["zoom"],
                pitch=48,
                bearing=24,
            ),
            layers=[
                pdk.Layer(
                    "ColumnLayer",
                    data=df_h,
                    get_position="[lon, lat]",
                    get_elevation="elevation",
                    elevation_scale=8,
                    radius="radius",
                    get_fill_color="color_rgba",
                    pickable=True,
                    auto_highlight=True,
                ),
                pdk.Layer(
                    "ScatterplotLayer",
                    data=df_h,
                    get_position="[lon, lat]",
                    get_radius=340,
                    radius_min_pixels=6,
                    stroked=True,
                    filled=True,
                    get_fill_color=[142, 216, 234, 230],
                    get_line_color=[232, 244, 255, 255],
                    line_width_min_pixels=2,
                    pickable=True,
                ),
            ],
            tooltip={
                "html": (
                    "<b>{corridor}</b><br/>"
                    "Predicted Risk: {risk_score} [{risk_score_lower} - {risk_score_upper}]<br/>"
                    "PM2.5: {pm25}<br/>NO2: {no2}<br/>"
                    "Confidence: {risk_score_confidence}"
                ),
            },
        )
        st.pydeck_chart(deck, use_container_width=True)
        st.caption(f"Forecast for T+{horizon}h. Column height = predicted risk. Hover for confidence intervals.")

    with fc2:
        st.markdown('<div class="section-title">Forecast Detail Table</div>', unsafe_allow_html=True)
        display_df = df_h[[
            "corridor", "risk_score", "risk_score_lower", "risk_score_upper",
            "pm25", "no2", "risk_score_confidence",
        ]].rename(columns={
            "corridor": "Corridor",
            "risk_score": "Risk",
            "risk_score_lower": "Low",
            "risk_score_upper": "High",
            "pm25": "PM2.5",
            "no2": "NO2",
            "risk_score_confidence": "Confidence",
        })
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Auto-generate recommended actions for high-risk corridors
        severe_corridors = df_h[df_h["risk_score"] >= 75]["corridor"].tolist()
        high_corridors = df_h[(df_h["risk_score"] >= 50) & (df_h["risk_score"] < 75)]["corridor"].tolist()

        if severe_corridors:
            st.error(f"**SEVERE risk predicted** at: {', '.join(severe_corridors)}")
            for sc in severe_corridors:
                store_action(
                    selected_city, sc, "escalation",
                    f"Predicted SEVERE risk at {horizon}h horizon — escalate monitoring.",
                    triggered_by="forecast_engine",
                )
        if high_corridors:
            st.warning(f"**HIGH risk predicted** at: {', '.join(high_corridors)}")

    # Confidence interval chart
    st.markdown('<div class="section-title">Prediction Confidence Intervals</div>', unsafe_allow_html=True)

    fig_ci = go.Figure()
    corridor_names = df_h["corridor"].tolist()
    fig_ci.add_trace(go.Bar(
        name="Risk (predicted)",
        x=corridor_names,
        y=df_h["risk_score"].tolist(),
        marker_color="#43c8e6",
    ))
    fig_ci.add_trace(go.Scatter(
        name="95% CI Upper",
        x=corridor_names,
        y=df_h["risk_score_upper"].tolist(),
        mode="markers",
        marker=dict(symbol="line-ew-open", size=12, color="#ffc857", line_width=2),
    ))
    fig_ci.add_trace(go.Scatter(
        name="95% CI Lower",
        x=corridor_names,
        y=df_h["risk_score_lower"].tolist(),
        mode="markers",
        marker=dict(symbol="line-ew-open", size=12, color="#66d0a2", line_width=2),
    ))
    fig_ci.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10,18,30,0.72)",
        font=dict(family="Space Grotesk, sans-serif", color="#c8d9eb"),
        height=320,
        margin=dict(l=0, r=0, t=12, b=60),
        xaxis=dict(tickangle=-35),
        barmode="group",
    )
    st.plotly_chart(fig_ci, use_container_width=True, config={"displayModeBar": False})

    # Model Explainability
    st.markdown('<div class="section-title">Model Explainability — Feature Importance</div>', unsafe_allow_html=True)

    fi_tab1, fi_tab2 = st.tabs(["Risk Score", "PM2.5"])
    for tab, target in [(fi_tab1, "risk_score"), (fi_tab2, "pm25")]:
        with tab:
            fi_df = model.feature_importance(target)
            fig_fi = go.Figure(go.Bar(
                x=fi_df["importance"].tolist(),
                y=fi_df["feature"].tolist(),
                orientation="h",
                marker_color="#9ea6ff",
            ))
            fig_fi.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(10,18,30,0.72)",
                font=dict(family="Space Grotesk, sans-serif", color="#c8d9eb"),
                height=340,
                margin=dict(l=0, r=0, t=8, b=8),
                yaxis=dict(autorange="reversed"),
                xaxis_title="Importance",
            )
            st.plotly_chart(fig_fi, use_container_width=True, config={"displayModeBar": False})

    # Prediction History from DB
    st.markdown('<div class="section-title">Prediction History & Audit</div>', unsafe_allow_html=True)

    hist_tab1, hist_tab2, hist_tab3 = st.tabs(["Recent Predictions", "Actions Log", "System Audit"])
    with hist_tab1:
        recent_preds = get_recent_predictions(selected_city, limit=60)
        if recent_preds:
            rp_df = pd.DataFrame(recent_preds)[
                ["created_at", "corridor", "horizon_h", "risk_score", "pm25", "no2", "confidence"]
            ]
            st.dataframe(rp_df, use_container_width=True, hide_index=True)
        else:
            st.info("No prediction history yet. Forecasts are recorded each time this page loads.")

    with hist_tab2:
        recent_acts = get_recent_actions(selected_city, limit=30)
        if recent_acts:
            st.dataframe(pd.DataFrame(recent_acts), use_container_width=True, hide_index=True)
        else:
            st.info("No actions recorded yet.")

    with hist_tab3:
        audit = get_audit_log(limit=50)
        if audit:
            st.dataframe(pd.DataFrame(audit), use_container_width=True, hide_index=True)
        else:
            st.info("No audit events yet.")

    st.markdown(
        '<div class="footer-note" style="margin-top:14px;">'
        "Forecasts are generated by XGBoost models trained on corridor simulation data. "
        "Confidence intervals represent 95% prediction bounds. All predictions are stored for continuous improvement."
        "</div>",
        unsafe_allow_html=True,
    )


def render_scenario_page(city_config: dict, selected_city: str, input_reset_token: str) -> None:  # noqa: C901
    import plotly.graph_objects as go
    import time as _time

    st.markdown(
        """
        <div class="hero">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap;">
            <div>
              <div style="font-size:0.85rem; color:#8bb8c8; letter-spacing:0.12em; text-transform:uppercase;">Live Event Simulation</div>
              <h1 class="hero-title" style="margin:0.2rem 0 0.35rem 0;">Air Quality Cinema - Watch It Unfold</h1>
              <div class="hero-subtitle">Press <b>Auto Run</b> to start. The chart grows frame by frame, spikes are detected, advisories are triggered, and the event log explains what is happening in real time.</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">Choose Scenario</div>', unsafe_allow_html=True)
    selected_scenario = st.radio(
        "scenario_picker",
        list(SCENARIOS.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )
    scenario = SCENARIOS[selected_scenario]
    st.markdown(
        f"""
        <div style="margin-top:8px; padding:10px 16px; background:rgba(67,200,230,0.05);
                    border-radius:10px; border:1px solid rgba(67,200,230,0.14);">
          <span style="font-size:0.85rem; color:#8bb8c8;">{scenario['icon']}</span>
          <span style="margin-left:10px; font-weight:600; color:#e6f0fa;">{selected_scenario}</span>
          <span style="margin-left:14px; color:#9bb1c6; font-size:0.86rem;">{scenario['description']}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    speed_opt = st.select_slider("Animation speed", options=["0.5x", "1x", "2x", "3x"], value="1x")
    speed_map = {"0.5x": 0.70, "1x": 0.35, "2x": 0.18, "3x": 0.09}
    frame_delay = speed_map[speed_opt]

    controller = ScenarioSimulationController(city_config, selected_city, selected_scenario, scenario)
    state = controller.ensure_state(f"{selected_city}|{selected_scenario}|{speed_opt}|{input_reset_token}")

    c1, c2, c3 = st.columns([1.2, 1.0, 2.8])
    with c1:
        btn_label = "Pause" if state.running else "Auto Run"
        if st.button(btn_label, use_container_width=True, type="primary"):
            st.session_state.scen_running = not state.running
            controller.add_log("[CTRL] Playback toggled.")
            st.rerun()
    with c2:
        if st.button("Reset", use_container_width=True):
            st.session_state.scenario_reset_token = "manual-reset"
            controller.add_log("[CTRL] Manual reset requested.")
            st.rerun()

    frame = st.session_state.scen_frame
    running = st.session_state.scen_running
    df_cur, avg_risk, max_pm25, avg_no2, _, phase_label, phase_color = controller.compute_frame(frame)
    current_time = f"T+{frame // 6:02d}:{(frame % 6) * 10:02d}"

    if not st.session_state.scen_history or st.session_state.scen_history[-1]["frame"] != frame:
        st.session_state.scen_history.append({
            "frame": frame,
            "time": current_time,
            "pm25": max_pm25,
            "risk": avg_risk,
        })

    if st.session_state.scen_phase != phase_label:
        st.session_state.scen_phase = phase_label
        controller.add_log(f"[PHASE] {current_time} -> {phase_label}")

    if avg_risk >= 75 and not any(a["level"] == "SEVERE" for a in st.session_state.scen_advisories):
        st.session_state.scen_advisories.append({"frame": frame, "time": current_time, "level": "SEVERE", "risk": avg_risk})
        controller.add_log(f"[ALERT] SEVERE advisory generated at {current_time} (risk {avg_risk}).")
    elif 50 <= avg_risk < 75 and not any(a["level"] in ("HIGH", "SEVERE") for a in st.session_state.scen_advisories):
        st.session_state.scen_advisories.append({"frame": frame, "time": current_time, "level": "HIGH", "risk": avg_risk})
        controller.add_log(f"[ALERT] HIGH advisory generated at {current_time} (risk {avg_risk}).")

    st.caption(f"Frame {frame} / {controller.TOTAL_FRAMES} | {current_time} | Phase: {phase_label} | Speed: {speed_opt}")

    hist_df = pd.DataFrame(st.session_state.scen_history)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist_df["frame"],
        y=hist_df["pm25"],
        name="PM2.5 ug/m3",
        mode="lines",
        line=dict(color="#ffc857", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(255,200,87,0.13)",
    ))
    fig.add_trace(go.Scatter(
        x=hist_df["frame"],
        y=hist_df["risk"],
        name="Risk Score",
        mode="lines",
        line=dict(color="#43c8e6", width=2, dash="dot"),
        yaxis="y2",
    ))
    for advisory in st.session_state.scen_advisories:
        marker_color = "#df7c8d" if advisory["level"] == "SEVERE" else "#f2bd6d"
        fig.add_vline(x=advisory["frame"], line_color=marker_color, line_dash="dash", line_width=1.8)
        fig.add_annotation(
            x=advisory["frame"],
            y=1.0,
            yref="paper",
            text=f"{advisory['level']} advisory",
            showarrow=False,
            font=dict(size=10, color=marker_color),
            bgcolor="rgba(14,26,43,0.90)",
            bordercolor=marker_color,
            borderwidth=1,
        )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10,18,30,0.72)",
        font=dict(family="Space Grotesk, sans-serif", color="#c8d9eb"),
        height=300,
        margin=dict(l=0, r=0, t=12, b=20),
        xaxis=dict(range=[0, controller.TOTAL_FRAMES], title="Frame"),
        yaxis=dict(title="PM2.5 ug/m3"),
        yaxis2=dict(title="Risk", overlaying="y", side="right", range=[0, 100]),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    metrics_a, metrics_b, metrics_c = st.columns(3)
    with metrics_a:
        st.metric("Peak PM2.5", max_pm25)
    with metrics_b:
        st.metric("Average Risk", avg_risk)
    with metrics_c:
        st.metric("Average NO2", avg_no2)

    if st.session_state.scen_advisories:
        latest = st.session_state.scen_advisories[-1]
        st.warning(f"Advisory generated: {latest['level']} at {latest['time']} with risk {latest['risk']}.")

    map_col, log_col = st.columns([1.6, 1.0])
    with map_col:
        deck = pdk.Deck(
            map_style="dark",
            initial_view_state=pdk.ViewState(
                latitude=city_config["center"]["lat"],
                longitude=city_config["center"]["lon"],
                zoom=city_config["center"]["zoom"],
                pitch=48,
                bearing=24,
            ),
            layers=[
                pdk.Layer(
                    "ColumnLayer",
                    data=df_cur,
                    get_position="[lon, lat]",
                    get_elevation="elevation",
                    elevation_scale=8,
                    radius="radius",
                    get_fill_color="sim_color_rgba",
                    pickable=True,
                ),
                pdk.Layer(
                    "ScatterplotLayer",
                    data=df_cur,
                    get_position="[lon, lat]",
                    get_radius=950,
                    get_fill_color=[67, 200, 230, 34],
                    pickable=False,
                ),
                pdk.Layer(
                    "ScatterplotLayer",
                    data=df_cur,
                    get_position="[lon, lat]",
                    get_radius=340,
                    radius_min_pixels=6,
                    stroked=True,
                    filled=True,
                    get_fill_color=[142, 216, 234, 230],
                    get_line_color=[232, 244, 255, 255],
                    line_width_min_pixels=2,
                    pickable=True,
                ),
            ],
            tooltip={"html": "<b>{corridor}</b><br/>Risk: {risk_score}<br/>PM2.5: {pm25_est}"},
        )
        st.pydeck_chart(deck, use_container_width=True)
        st.caption("Simulation gradient: green -> yellow -> orange -> red as risk increases.")

    with log_col:
        st.markdown('<div class="section-title">Simulation Log</div>', unsafe_allow_html=True)
        st.code("\n".join(st.session_state.scen_logs[-14:]), language="text")

    st.markdown(
        f"<div style='color:#7a9ab4; font-size:0.8rem;'>Current phase: <span style='color:{phase_color};'>{phase_label}</span></div>",
        unsafe_allow_html=True,
    )

    if running:
        if frame < controller.TOTAL_FRAMES:
            _time.sleep(frame_delay)
            st.session_state.scen_frame += 1
            st.rerun()
        else:
            st.session_state.scen_running = False
            controller.add_log("[DONE] Playback completed. Ready for re-run.")


@dataclass
class SidebarControls:
    page: str
    selected_city: str
    traffic_volume: int
    inversion_strength: int
    industrial_activity: int
    wind_speed: int
    humidity: int
    emergency_event: bool


class TAQOISApp:
    def render_hero(self) -> None:
        st.markdown(
            """
            <div class="hero">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap;">
                <div>
                  <div style="font-size:0.85rem; color:#8bb8c8; letter-spacing:0.12em; text-transform:uppercase;">Toronto Air Quality Operations Intelligence System</div>
                  <h1 class="hero-title" style="margin:0.2rem 0 0.35rem 0;">TAQOIS / Command and Control Center</h1>
                  <div class="hero-subtitle">Cyberpunk-Enterprise simulation platform for corridor-level air quality stress testing, response orchestration, and executive intelligence.</div>
                </div>
                <div>
                  <span class="alert-chip" style="background:rgba(67,200,230,0.12); color:#8ed8ea;">3D Geospatial Ops</span>
                  <span class="alert-chip" style="background:rgba(158,166,255,0.12); color:#c2c7ff;">XGBoost Forecast</span>
                  <span class="alert-chip" style="background:rgba(102,208,162,0.12); color:#8fe0bc;">Real-Time Ingestion</span>
                  <span class="alert-chip" style="background:rgba(242,189,109,0.12); color:#f2bd6d;">Decision Support</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def render_sidebar(self) -> SidebarControls:
        with st.sidebar:
            st.header("TAQOIS Navigation")
            page = st.radio("page_nav", ["Dashboard", "AI Forecast", "Scenario Simulation"], label_visibility="collapsed")
            st.markdown("---")
            selected_city = st.selectbox("City", list(CITY_PRESETS.keys()), index=0)
            st.caption("Use this to switch the simulation focus city.")

            st.subheader("Simulation Controls")
            traffic_volume = st.slider("Traffic Volume", 0, 100, 72)
            inversion_strength = st.slider("Weather Inversion", 0, 100, 58)
            industrial_activity = st.slider("Industrial Activity", 0, 100, 61)
            wind_speed = st.slider("Wind Speed (km/h)", 0, 60, 18)
            humidity = st.slider("Humidity (%)", 10, 100, 67)
            emergency_event = st.toggle("Special Event / Incident Surge", value=False)

            st.markdown("---")
            st.caption("XGBoost Forecast + Deterministic Sim Engine")
            st.caption("Forecasts use ML models. Briefings adapt to conditions.")

        return SidebarControls(
            page=page,
            selected_city=selected_city,
            traffic_volume=traffic_volume,
            inversion_strength=inversion_strength,
            industrial_activity=industrial_activity,
            wind_speed=wind_speed,
            humidity=humidity,
            emergency_event=emergency_event,
        )

    def render_dashboard(self, controls: SidebarControls, city_config: Dict) -> None:
        sim_inputs = SimulationInputs(
            traffic_volume=controls.traffic_volume,
            inversion_strength=controls.inversion_strength,
            industrial_activity=controls.industrial_activity,
            wind_speed=controls.wind_speed,
            humidity=controls.humidity,
            emergency_event=controls.emergency_event,
        )
        engine = SimulationEngine(city_config["corridors"])
        df = engine.run(sim_inputs)

        avg_risk = round(df["risk_score"].mean(), 1)
        max_risk = round(df["risk_score"].max(), 1)
        hotspots = int((df["risk_score"] >= 75).sum())
        status = city_status(avg_risk)
        worst = df.iloc[0]["corridor"]

        st.markdown(
            f"""
            <div class="metric-grid">
                <div class="metric-card"><div class="metric-label">Citywide Status</div><div class="metric-value">{status}</div><div class="metric-delta">Average risk {avg_risk} in {controls.selected_city}</div></div>
                <div class="metric-card"><div class="metric-label">Critical Hotspots</div><div class="metric-value">{hotspots}</div><div class="metric-delta">Corridors at severe threshold</div></div>
                <div class="metric-card"><div class="metric-label">Peak Corridor Risk</div><div class="metric-value">{max_risk}</div><div class="metric-delta">{worst}</div></div>
                <div class="metric-card"><div class="metric-label">Primary Drivers</div><div class="metric-value">{controls.traffic_volume}/{controls.inversion_strength}/{controls.industrial_activity}</div><div class="metric-delta">Traffic / inversion / industry</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        city_center = city_config["center"]
        col1, col2 = st.columns([1.35, 1])
        with col1:
            st.markdown('<div class="section-title">Spatial Intelligence</div>', unsafe_allow_html=True)
            st.subheader("3D Corridor Risk Map")
            deck = pdk.Deck(
                map_style="dark",
                initial_view_state=pdk.ViewState(
                    latitude=city_center["lat"],
                    longitude=city_center["lon"],
                    zoom=city_center["zoom"],
                    pitch=48,
                    bearing=24,
                ),
                layers=[
                    pdk.Layer(
                        "ColumnLayer",
                        data=df,
                        get_position='[lon, lat]',
                        get_elevation="elevation",
                        elevation_scale=8,
                        radius="radius",
                        get_fill_color="color_rgba",
                        pickable=True,
                        auto_highlight=True,
                    ),
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=df,
                        get_position='[lon, lat]',
                        get_radius=900,
                        get_fill_color=[67, 200, 230, 36],
                        pickable=False,
                    ),
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=df,
                        get_position='[lon, lat]',
                        get_radius=320,
                        radius_min_pixels=6,
                        stroked=True,
                        filled=True,
                        get_fill_color=[142, 216, 234, 230],
                        get_line_color=[232, 244, 255, 255],
                        line_width_min_pixels=2,
                        pickable=True,
                    ),
                ],
                tooltip={
                    "html": "<b>{corridor}</b><br/>Risk: {risk_score}<br/>Level: {risk_level}<br/>PM2.5: {pm25_est}<br/>NO2: {no2_est}",
                    "style": {
                        "backgroundColor": "#0e1a2b",
                        "color": "#eef6ff",
                        "border": "1px solid #43c8e6",
                        "borderRadius": "10px",
                        "fontSize": "13px",
                        "padding": "10px",
                    },
                },
            )
            st.pydeck_chart(deck, use_container_width=True)
            st.caption(
                "Map legend: Dot = corridor location. Column height = risk intensity. Column color = risk band (green low, cyan elevated, amber high, red severe)."
            )

        with col2:
            st.markdown('<div class="section-title">Threat Analytics</div>', unsafe_allow_html=True)
            st.subheader("Corridor Threat Matrix")
            styled = df[["corridor", "risk_score", "risk_level", "pm25_est", "no2_est", "exposure_index"]].rename(
                columns={
                    "corridor": "Corridor",
                    "risk_score": "Risk",
                    "risk_level": "Level",
                    "pm25_est": "PM2.5",
                    "no2_est": "NO2",
                    "exposure_index": "Exposure",
                }
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)
            st.markdown(
                f"""
                **What these numbers mean (simple):**
                - **Risk**: overall stress score from 0 to 100 (higher means worse).
                - **PM2.5 / NO2**: estimated pollution concentration indicators.
                - **Exposure**: combined impact estimate that also considers nearby population pressure.
                - **Top concern now**: **{worst}** with risk **{max_risk}**.
                """
            )

        summary_payload = {
            "city": controls.selected_city,
            "citywide_status": status,
            "avg_risk": avg_risk,
            "max_risk": max_risk,
            "top_corridors": df["corridor"].head(3).tolist(),
            "top_risks": df["risk_score"].head(3).tolist(),
            "drivers": {
                "traffic_volume": controls.traffic_volume,
                "weather_inversion": controls.inversion_strength,
                "industrial_activity": controls.industrial_activity,
                "wind_speed": controls.wind_speed,
                "humidity": controls.humidity,
                "special_event": controls.emergency_event,
            },
        }

        intel = generate_intel(summary_payload)
        tab1, tab2, tab3 = st.tabs(["Executive Briefing", "Tactical Response Plan", "Public Health Advisory"])

        with tab1:
            st.write(intel["executive_briefing"])
        with tab2:
            st.write(intel["tactical_response_plan"])
        with tab3:
            st.write(intel["public_health_advisory"])

        st.markdown(
            """
            <div class="footer-note" style="margin-top:14px;">
              Simulation only. Corridor values are synthetic and designed for command-center prototyping, not regulatory reporting.
            </div>
            """,
            unsafe_allow_html=True,
        )

    def run(self) -> None:
        controls = self.render_sidebar()
        city_config = CITY_PRESETS[controls.selected_city]

        if controls.page == "AI Forecast":
            render_forecast_page(city_config, controls.selected_city, controls)
            return

        if controls.page == "Scenario Simulation":
            scenario_input_token = (
                f"{controls.traffic_volume}|{controls.inversion_strength}|{controls.industrial_activity}|"
                f"{controls.wind_speed}|{controls.humidity}|{int(controls.emergency_event)}"
            )
            render_scenario_page(city_config, controls.selected_city, scenario_input_token)
            return

        self.render_hero()
        self.render_dashboard(controls, city_config)


TAQOISApp().run()
