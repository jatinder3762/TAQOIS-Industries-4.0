"""
TAQOIS Forecast Engine
XGBoost-based short-term air-quality forecasting (2-6 hour horizon).
Generates synthetic training data from the simulation model, trains an
XGBoost regressor, and produces predictions with confidence intervals.
"""

import logging
import pickle
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / ".models"
MODEL_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Synthetic training-data generator
# ---------------------------------------------------------------------------

def _generate_training_data(corridors: List[Dict], n_samples: int = 6000) -> pd.DataFrame:
    """
    Generate synthetic but realistic training samples that mimic
    the relationships between environmental conditions and air-quality
    outcomes for each corridor.
    """
    rng = np.random.default_rng(42)
    rows = []
    for _ in range(n_samples):
        c = corridors[rng.integers(len(corridors))]

        traffic = rng.uniform(10, 100)
        inversion = rng.uniform(0, 100)
        industrial = rng.uniform(10, 100)
        wind = rng.uniform(0, 60)
        humidity = rng.uniform(10, 100)
        temperature = rng.uniform(-10, 40)
        hour = rng.integers(0, 24)
        day_of_week = rng.integers(0, 7)
        month = rng.integers(1, 13)
        emergency = rng.choice([0, 1], p=[0.92, 0.08])

        # Rush hour effect
        rush_mult = 1.0
        if 7 <= hour <= 9 or 16 <= hour <= 18:
            rush_mult = 1.25
        # Weekend discount
        weekend_mult = 0.82 if day_of_week >= 5 else 1.0
        # Seasonal (summer worse)
        season_mult = 1.0 + 0.15 * np.sin((month - 1) * np.pi / 6)

        weather_relief = max(0.35, 1 - wind / 160)
        humidity_penalty = humidity / 250

        idx_noise = rng.integers(len(corridors))
        traffic_factor = (traffic / 100) * (1.05 + idx_noise * 0.015) * rush_mult * weekend_mult
        inversion_factor = (inversion / 100) * 1.25
        industrial_factor = (industrial / 100) * (1.0 + (0.12 if "Industrial" in c["name"] else 0.0))
        emergency_penalty = 0.18 if emergency else 0.0

        raw_score = (
            22 * traffic_factor
            + 27 * inversion_factor
            + 18 * industrial_factor
            + 16 * c["population_index"]
            + 10 * humidity_penalty
            + 7 * emergency_penalty
        ) * c["sensitivity"] * weather_relief * season_mult

        risk_score = max(0, min(100, raw_score + rng.normal(0, 3.5)))
        pm25 = max(0, c["baseline_pm25"] + risk_score * 0.23 + rng.normal(0, 1.8))
        no2 = max(0, c["baseline_no2"] + risk_score * 0.31 + rng.normal(0, 2.2))

        rows.append({
            "corridor_name": c["name"],
            "corridor_sensitivity": c["sensitivity"],
            "corridor_population_index": c["population_index"],
            "corridor_baseline_pm25": c["baseline_pm25"],
            "corridor_baseline_no2": c["baseline_no2"],
            "traffic_volume": traffic,
            "inversion_strength": inversion,
            "industrial_activity": industrial,
            "wind_speed": wind,
            "humidity": humidity,
            "temperature_c": temperature,
            "hour": hour,
            "day_of_week": day_of_week,
            "month": month,
            "emergency_event": emergency,
            "risk_score": round(risk_score, 2),
            "pm25": round(pm25, 2),
            "no2": round(no2, 2),
        })

    return pd.DataFrame(rows)


FEATURE_COLS = [
    "corridor_sensitivity",
    "corridor_population_index",
    "corridor_baseline_pm25",
    "corridor_baseline_no2",
    "traffic_volume",
    "inversion_strength",
    "industrial_activity",
    "wind_speed",
    "humidity",
    "temperature_c",
    "hour",
    "day_of_week",
    "month",
    "emergency_event",
]


# ---------------------------------------------------------------------------
# Model wrapper
# ---------------------------------------------------------------------------

class AQForecastModel:
    """Wraps three XGBoost regressors: risk_score, pm25, no2."""

    def __init__(self):
        self.models: Dict = {}
        self.trained = False
        self._residual_std: Dict[str, float] = {}

    def train(self, corridors: List[Dict], n_samples: int = 6000) -> Dict[str, float]:
        from xgboost import XGBRegressor

        df = _generate_training_data(corridors, n_samples)
        X = df[FEATURE_COLS].values
        metrics = {}
        for target in ("risk_score", "pm25", "no2"):
            y = df[target].values
            model = XGBRegressor(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.08,
                subsample=0.85,
                colsample_bytree=0.85,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=42,
                verbosity=0,
            )
            model.fit(X, y)
            self.models[target] = model
            preds = model.predict(X)
            rmse = float(np.sqrt(np.mean((y - preds) ** 2)))
            self._residual_std[target] = float(np.std(y - preds))
            metrics[f"{target}_rmse"] = round(rmse, 3)
            logger.info("Trained %s model – RMSE: %.3f", target, rmse)

        self.trained = True
        self._save()
        return metrics

    def predict(
        self,
        corridors: List[Dict],
        conditions: Dict,
        horizons_hours: List[int] = None,
    ) -> pd.DataFrame:
        if not self.trained:
            self._load()
        if not self.trained:
            raise RuntimeError("Model not trained. Call train() first.")

        if horizons_hours is None:
            horizons_hours = [2, 4, 6]

        now = datetime.now(timezone.utc)
        rows = []
        for h in horizons_hours:
            future = now + timedelta(hours=h)
            for c in corridors:
                features = self._build_features(c, conditions, future)
                X = np.array([features])
                preds = {}
                for target in ("risk_score", "pm25", "no2"):
                    val = float(self.models[target].predict(X)[0])
                    std = self._residual_std.get(target, 3.0)
                    preds[target] = max(0, round(val, 1))
                    preds[f"{target}_lower"] = max(0, round(val - 1.96 * std, 1))
                    preds[f"{target}_upper"] = round(val + 1.96 * std, 1)
                    preds[f"{target}_confidence"] = round(
                        max(0.0, min(1.0, 1.0 - (std / (abs(val) + 1e-6)) * 0.3)), 2
                    )

                rows.append({
                    "corridor": c["name"],
                    "lat": c["lat"],
                    "lon": c["lon"],
                    "horizon_hours": h,
                    "forecast_time": future.isoformat(),
                    **preds,
                })

        return pd.DataFrame(rows)

    def feature_importance(self, target: str = "risk_score") -> pd.DataFrame:
        if not self.trained:
            self._load()
        model = self.models.get(target)
        if model is None:
            return pd.DataFrame()
        importance = model.feature_importances_
        return (
            pd.DataFrame({"feature": FEATURE_COLS, "importance": importance})
            .sort_values("importance", ascending=False)
            .reset_index(drop=True)
        )

    def _build_features(self, corridor: Dict, conditions: Dict, dt: datetime) -> List[float]:
        return [
            corridor["sensitivity"],
            corridor["population_index"],
            corridor["baseline_pm25"],
            corridor["baseline_no2"],
            conditions.get("traffic_volume", 50),
            conditions.get("inversion_strength", 30),
            conditions.get("industrial_activity", 40),
            conditions.get("wind_speed", 15),
            conditions.get("humidity", 50),
            conditions.get("temperature_c", 20),
            dt.hour,
            dt.weekday(),
            dt.month,
            conditions.get("emergency_event", 0),
        ]

    def _save(self) -> None:
        path = MODEL_DIR / "aq_forecast.pkl"
        try:
            with open(path, "wb") as f:
                pickle.dump(
                    {"models": self.models, "residual_std": self._residual_std},
                    f,
                )
        except Exception as exc:
            logger.warning("Failed to save models: %s", exc)

    def _load(self) -> None:
        path = MODEL_DIR / "aq_forecast.pkl"
        if not path.exists():
            return
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            self.models = data["models"]
            self._residual_std = data.get("residual_std", {})
            self.trained = True
        except Exception as exc:
            logger.warning("Failed to load models: %s", exc)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_instance: Optional[AQForecastModel] = None


def get_forecast_model() -> AQForecastModel:
    global _instance
    if _instance is None:
        _instance = AQForecastModel()
    return _instance
