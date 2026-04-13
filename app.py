import os
import random
from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd
import pydeck as pdk
import streamlit as st
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except Exception:
    genai = None


load_dotenv(override=False)


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


class GeminiCOO:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.enabled = bool(self.api_key) and genai is not None
        if self.enabled:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash")

    def generate(self, summary_payload: Dict) -> Dict[str, str]:
        if not self.enabled:
            return self._fallback(summary_payload)

        city = summary_payload.get("city", "the selected city")
        prompt = f"""
You are the Chief Operations Officer for {city} Air Quality Operations Intelligence System (TAQOIS).
Analyze this simulated state and produce:
1) Executive Briefing
2) Tactical Response Plan
3) Public Health Advisory

Constraints:
- Be precise, concise, executive-ready.
- Use {city} corridor names exactly as provided.
- Mention the top 3 highest-risk corridors.
- Include urgency level and next 2-hour operational posture.
- Public advisory must be plain-language.

Simulation state:
{summary_payload}
"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            return self._parse_sections(text)
        except Exception:
            return self._fallback(summary_payload)

    def _parse_sections(self, text: str) -> Dict[str, str]:
        sections = {
            "executive_briefing": "",
            "tactical_response_plan": "",
            "public_health_advisory": "",
        }
        current = None
        for line in text.splitlines():
            line_stripped = line.strip().lower()
            if "executive" in line_stripped and "brief" in line_stripped:
                current = "executive_briefing"
                continue
            if "tactical" in line_stripped and "response" in line_stripped:
                current = "tactical_response_plan"
                continue
            if "public" in line_stripped and ("advisory" in line_stripped or "health" in line_stripped):
                current = "public_health_advisory"
                continue
            if current:
                sections[current] += line + "\n"
        if not any(v.strip() for v in sections.values()):
            return self._fallback({"raw_text": text})
        return {k: v.strip() for k, v in sections.items()}

    def _fallback(self, payload: Dict) -> Dict[str, str]:
        city = payload.get("city", "the selected city")
        top = payload["top_corridors"]
        avg = payload["avg_risk"]
        urgency = payload["citywide_status"]
        return {
            "executive_briefing": (
                f"{city} air-quality simulation indicates a {urgency} citywide posture with an average corridor risk score of {avg}. "
                f"Highest-risk corridors are {top[0]}, {top[1]}, and {top[2]}. "
                f"Immediate focus should prioritize traffic flow smoothing, industrial emissions coordination, and targeted public messaging over the next 2 hours."
            ),
            "tactical_response_plan": (
                "1. Activate corridor monitoring escalation for the top three hotspots.\n"
                "2. Coordinate with transportation control to reduce stop-and-go congestion on affected links.\n"
                "3. Notify industrial compliance partners in impacted zones to minimize discretionary emissions.\n"
                "4. Push public health advisories to sensitive populations near severe and high-risk corridors.\n"
                "5. Re-run simulation every 15 minutes and escalate to municipal emergency coordination if two or more corridors remain in Severe status."
            ),
            "public_health_advisory": (
                f"Air quality is currently under {urgency.lower()} pressure in parts of {city}, especially near {top[0]}, {top[1]}, and {top[2]}. "
                "Children, older adults, and people with asthma or heart and lung conditions should limit strenuous outdoor activity near major roads and industrial areas today. "
                "Keep windows closed where possible and use indoor air filtration if available."
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

    st.markdown('<div class="glass">', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)

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
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Simulation Log</div>', unsafe_allow_html=True)
        st.code("\n".join(st.session_state.scen_logs[-14:]), language="text")
        st.markdown('</div>', unsafe_allow_html=True)

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
                  <span class="alert-chip" style="background:rgba(158,166,255,0.12); color:#c2c7ff;">Gemini COO</span>
                  <span class="alert-chip" style="background:rgba(102,208,162,0.12); color:#8fe0bc;">Simulation Engine</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def render_sidebar(self) -> SidebarControls:
        with st.sidebar:
            st.header("TAQOIS Navigation")
            page = st.radio("page_nav", ["Dashboard", "Scenario Simulation"], label_visibility="collapsed")
            st.markdown("---")
            st.subheader("Simulation Controls")
            selected_city = st.selectbox("City", list(CITY_PRESETS.keys()), index=0)
            st.caption("Use this to switch the simulation focus city.")

            traffic_volume = st.slider("Traffic Volume", 0, 100, 72)
            inversion_strength = st.slider("Weather Inversion", 0, 100, 58)
            industrial_activity = st.slider("Industrial Activity", 0, 100, 61)
            wind_speed = st.slider("Wind Speed (km/h)", 0, 60, 18)
            humidity = st.slider("Humidity (%)", 10, 100, 67)
            emergency_event = st.toggle("Special Event / Incident Surge", value=False)

            st.markdown("---")
            st.caption("Gemini 2.5 Flash")
            st.code("Set GEMINI_API_KEY in your environment to enable live AI briefings.", language="bash")

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

        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Operator Guide</div>', unsafe_allow_html=True)
        with st.expander("New user? Click for a simple dashboard walkthrough", expanded=False):
            st.markdown(
                """
                1. Pick a city in the left sidebar.
                2. Adjust sliders to simulate traffic, weather inversion, industry load, and weather impact.
                3. Watch the city status cards update in real time.
                4. On the map: cyan dots show where each corridor is, while colored 3D columns show how serious the risk is.
                5. Hover a column to see PM2.5, NO2, and risk details.
                6. Use the AI tabs to get executive summary, response plan, and public health message.
                """
            )

        st.info(
            f"Now monitoring: {controls.selected_city}. This screen shows simulated operational air-risk indicators by corridor, not live regulatory readings yet."
        )
        st.markdown('</div>', unsafe_allow_html=True)

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
            st.markdown('<div class="glass">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="glass">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)

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

        coo = GeminiCOO()
        intel = coo.generate(summary_payload)
        tab1, tab2, tab3 = st.tabs(["Executive Briefing", "Tactical Response Plan", "Public Health Advisory"])

        with tab1:
            st.markdown('<div class="glass">', unsafe_allow_html=True)
            st.write(intel["executive_briefing"])
            st.markdown('</div>', unsafe_allow_html=True)
        with tab2:
            st.markdown('<div class="glass">', unsafe_allow_html=True)
            st.write(intel["tactical_response_plan"])
            st.markdown('</div>', unsafe_allow_html=True)
        with tab3:
            st.markdown('<div class="glass">', unsafe_allow_html=True)
            st.write(intel["public_health_advisory"])
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            """
            <div class="footer-note" style="margin-top:14px;">
              Simulation only. Corridor values are synthetic and designed for command-center prototyping, not regulatory reporting.
            </div>
            """,
            unsafe_allow_html=True,
        )

    def run(self) -> None:
        self.render_hero()
        controls = self.render_sidebar()
        city_config = CITY_PRESETS[controls.selected_city]

        if controls.page == "Scenario Simulation":
            scenario_input_token = (
                f"{controls.traffic_volume}|{controls.inversion_strength}|{controls.industrial_activity}|"
                f"{controls.wind_speed}|{controls.humidity}|{int(controls.emergency_event)}"
            )
            render_scenario_page(city_config, controls.selected_city, scenario_input_token)
            return

        self.render_dashboard(controls, city_config)


TAQOISApp().run()
