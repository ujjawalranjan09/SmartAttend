"""
Feature extraction for proxy attendance detection.
Converts attendance record data into a normalized feature vector.
"""


def extract_features(record: dict) -> list[float]:
    """
    Extract a normalized feature vector from an attendance record dict.

    Expected input keys:
        - geo_accuracy_m: GPS accuracy in meters (0 if not available)
        - wifi_bssid_present: 1 if WiFi BSSID was captured, else 0
        - ble_beacon_present: 1 if BLE beacon was detected, else 0
        - face_confidence: Face verification confidence (0-1)
        - device_fingerprint_present: 1 if device fingerprint was provided, else 0
        - time_deviation_seconds: Minutes deviation from session start time
        - historical_avg_time: Student's historical average check-in time deviation

    Returns:
        Normalized feature vector of 7 floats, each in [0, 1] range.
    """
    geo_accuracy = record.get("geo_accuracy_m", 0)
    wifi_present = record.get("wifi_bssid_present", 0)
    ble_present = record.get("ble_beacon_present", 0)
    face_conf = record.get("face_confidence", 0)
    device_fp = record.get("device_fingerprint_present", 0)
    time_dev = record.get("time_deviation_seconds", 0)
    hist_avg = record.get("historical_avg_time", 0)

    # Normalize GPS accuracy: 0m = 0, 500m+ = 1
    geo_norm = min(1.0, geo_accuracy / 500.0)

    # Normalize time deviation: 0s = 0, 3600s+ (1 hour) = 1
    time_norm = min(1.0, abs(time_dev) / 3600.0)

    # Normalize historical average: 0s = 0, 1800s+ (30 min) = 1
    hist_norm = min(1.0, abs(hist_avg) / 1800.0)

    return [
        geo_norm,
        float(wifi_present),
        float(ble_present),
        float(face_conf),
        float(device_fp),
        time_norm,
        hist_norm,
    ]