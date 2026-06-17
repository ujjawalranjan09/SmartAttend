"""Tests for attendance forecast endpoint."""
from datetime import datetime, timedelta
import numpy as np


class TestForecast:
    def test_forecast_returns_14_days(self, client, sample_time_series):
        """POST /forecast/predict returns 14-day forecast."""
        response = client.post(
            "/api/v1/forecast/predict",
            json=sample_time_series,
        )
        assert response.status_code == 200
        data = response.json()
        assert "forecast" in data
        assert len(data["forecast"]) == 14
        assert "trend_direction" in data
        assert data["trend_direction"] in ("improving", "declining", "stable")
        assert "next_7d_avg" in data
        assert "next_14d_avg" in data

    def test_forecast_values_in_range(self, client, sample_time_series):
        """Forecast values are within 0-100."""
        response = client.post(
            "/api/v1/forecast/predict",
            json=sample_time_series,
        )
        data = response.json()
        for day in data["forecast"]:
            assert 0.0 <= day["predicted_pct"] <= 100.0
            assert 0.0 <= day["lower_bound"] <= 100.0
            assert 0.0 <= day["upper_bound"] <= 100.0
            assert day["lower_bound"] <= day["upper_bound"]

    def test_forecast_has_correct_structure(self, client, sample_time_series):
        """Each forecast entry has the required fields."""
        response = client.post(
            "/api/v1/forecast/predict",
            json=sample_time_series,
        )
        data = response.json()
        for day in data["forecast"]:
            assert "date" in day
            assert "predicted_pct" in day
            assert "lower_bound" in day
            assert "upper_bound" in day

    def test_short_history_uses_linear_fallback(self, client):
        """Fewer than 14 data points still returns valid forecast."""
        short_data = [
            {"date": "2024-01-01", "attendance_pct": 80.0},
            {"date": "2024-01-02", "attendance_pct": 82.0},
            {"date": "2024-01-03", "attendance_pct": 81.0},
        ]
        response = client.post(
            "/api/v1/forecast/predict",
            json=short_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["forecast"]) == 14

    def test_single_point_forecast(self, client):
        """Single data point returns flat forecast."""
        data = [{"date": "2024-01-01", "attendance_pct": 85.0}]
        response = client.post(
            "/api/v1/forecast/predict",
            json=data,
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["forecast"]) == 14
        for day in result["forecast"]:
            assert day["predicted_pct"] == 85.0

    def test_forecast_with_trend(self, client):
        """Improving trend is detected."""
        data = []
        for i in range(30):
            date = (datetime.utcnow() - timedelta(days=30 - i)).strftime("%Y-%m-%d")
            pct = 60 + i * 1.0  # Clearly improving
            data.append({"date": date, "attendance_pct": round(pct, 2)})

        response = client.post(
            "/api/v1/forecast/predict",
            json=data,
        )
        assert response.status_code == 200
        result = response.json()
        assert result["trend_direction"] == "improving"
        assert result["next_7d_avg"] > data[-1]["attendance_pct"]