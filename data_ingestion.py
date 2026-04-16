"""
TAQOIS Data Ingestion Module
Fetches real-time weather and air-quality data from public APIs.
Falls back to cached / synthetic data when APIs are unavailable.
"""

import os
import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

CACHE_TTL_SECONDS = 900  # 15 minutes


def _cache_key(prefix: str, params: dict) -> str:
    raw = json.dumps(params, sort_keys=True)
    return prefix + "_" + hashlib.md5(raw.encode()).hexdigest()


def _read_cache(key: str) -> Optional[dict]:
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - data.get("_ts", 0) < CACHE_TTL_SECONDS:
            return data
    except Exception:
        pass
    return None


def _write_cache(key: str, data: dict) -> None:
    data["_ts"] = time.time()
    path = CACHE_DIR / f"{key}.json"
    try:
        path.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# OpenWeatherMap (free tier – Current Weather)
# ---------------------------------------------------------------------------

def fetch_weather(lat: float, lon: float) -> Dict:
    api_key = os.getenv("OPENWEATHER_API_KEY", "")
    cache_k = _cache_key("weather", {"lat": round(lat, 3), "lon": round(lon, 3)})
    cached = _read_cache(cache_k)
    if cached:
        cached.pop("_ts", None)
        return cached

    if not api_key:
        return _synthetic_weather(lat, lon)

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        raw = resp.json()
        result = {
            "temperature_c": raw["main"]["temp"],
            "humidity": raw["main"]["humidity"],
            "wind_speed_kmh": round(raw["wind"]["speed"] * 3.6, 1),
            "wind_deg": raw["wind"].get("deg", 0),
            "pressure_hpa": raw["main"]["pressure"],
            "description": raw["weather"][0]["description"] if raw.get("weather") else "",
            "clouds_pct": raw.get("clouds", {}).get("all", 0),
            "source": "openweathermap",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_cache(cache_k, result)
        return result
    except Exception as exc:
        logger.warning("OpenWeatherMap fetch failed for (%.3f, %.3f): %s", lat, lon, exc)
        return _synthetic_weather(lat, lon)


def _synthetic_weather(lat: float, lon: float) -> Dict:
    import random
    seed = int((lat * 1000 + lon * 1000 + time.time() // 3600) % 10000)
    rng = random.Random(seed)
    return {
        "temperature_c": round(rng.uniform(-5, 35), 1),
        "humidity": rng.randint(25, 95),
        "wind_speed_kmh": round(rng.uniform(2, 45), 1),
        "wind_deg": rng.randint(0, 360),
        "pressure_hpa": rng.randint(995, 1030),
        "description": rng.choice(["clear sky", "few clouds", "overcast", "light rain", "haze"]),
        "clouds_pct": rng.randint(0, 100),
        "source": "synthetic_fallback",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# AQICN (World Air Quality Index) – free token
# ---------------------------------------------------------------------------

def fetch_air_quality(lat: float, lon: float) -> Dict:
    token = os.getenv("AQICN_API_TOKEN", "")
    cache_k = _cache_key("aq", {"lat": round(lat, 3), "lon": round(lon, 3)})
    cached = _read_cache(cache_k)
    if cached:
        cached.pop("_ts", None)
        return cached

    if not token:
        return _synthetic_air_quality(lat, lon)

    url = f"https://api.waqi.info/feed/geo:{lat};{lon}/"
    params = {"token": token}
    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        raw = resp.json()
        if raw.get("status") != "ok":
            raise ValueError(f"AQICN status: {raw.get('status')}")
        data = raw["data"]
        iaqi = data.get("iaqi", {})
        result = {
            "aqi": data.get("aqi", -1),
            "pm25": iaqi.get("pm25", {}).get("v"),
            "pm10": iaqi.get("pm10", {}).get("v"),
            "no2": iaqi.get("no2", {}).get("v"),
            "so2": iaqi.get("so2", {}).get("v"),
            "o3": iaqi.get("o3", {}).get("v"),
            "co": iaqi.get("co", {}).get("v"),
            "dominant_pollutant": data.get("dominentpol", ""),
            "station": data.get("city", {}).get("name", ""),
            "source": "aqicn",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_cache(cache_k, result)
        return result
    except Exception as exc:
        logger.warning("AQICN fetch failed for (%.3f, %.3f): %s", lat, lon, exc)
        return _synthetic_air_quality(lat, lon)


def _synthetic_air_quality(lat: float, lon: float) -> Dict:
    import random
    seed = int((lat * 1000 + lon * 1000 + time.time() // 3600) % 10000)
    rng = random.Random(seed)
    return {
        "aqi": rng.randint(20, 180),
        "pm25": round(rng.uniform(4, 60), 1),
        "pm10": round(rng.uniform(8, 90), 1),
        "no2": round(rng.uniform(5, 55), 1),
        "so2": round(rng.uniform(1, 20), 1),
        "o3": round(rng.uniform(10, 80), 1),
        "co": round(rng.uniform(0.2, 3.0), 1),
        "dominant_pollutant": rng.choice(["pm25", "pm10", "o3", "no2"]),
        "station": "synthetic",
        "source": "synthetic_fallback",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Corridor-level data aggregation
# ---------------------------------------------------------------------------

def fetch_corridor_conditions(corridors: List[Dict]) -> List[Dict]:
    """Fetch weather + AQ for each corridor and return enriched records."""
    results = []
    for c in corridors:
        weather = fetch_weather(c["lat"], c["lon"])
        aq = fetch_air_quality(c["lat"], c["lon"])
        results.append({
            "corridor": c["name"],
            "lat": c["lat"],
            "lon": c["lon"],
            "weather": weather,
            "air_quality": aq,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    return results


def conditions_to_sim_inputs(weather: Dict) -> Dict:
    """Convert real weather data into simulation slider equivalents."""
    wind = weather.get("wind_speed_kmh", 15)
    humidity = weather.get("humidity", 50)
    temp = weather.get("temperature_c", 20)

    # Inversion proxy: low wind + high pressure + low clouds
    pressure = weather.get("pressure_hpa", 1013)
    clouds = weather.get("clouds_pct", 50)
    inversion_raw = max(0, (pressure - 1005) * 1.5 + (100 - clouds) * 0.3 - wind * 1.2)
    inversion_strength = int(min(100, max(0, inversion_raw)))

    return {
        "wind_speed": int(min(60, max(0, wind))),
        "humidity": int(min(100, max(10, humidity))),
        "inversion_strength": inversion_strength,
        "temperature_c": temp,
    }
