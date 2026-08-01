try:
    from geopy.distance import geodesic
except Exception:
    geodesic = None

from config import DANGEROUS_ANIMALS


def _haversine_km(a, b):
    # Lightweight fallback using the haversine formula if geopy is not available.
    import math

    lat1, lon1 = a
    lat2, lon2 = b
    R = 6371.0  # Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    hav = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(hav), math.sqrt(1 - hav))
    return R * c


def calculate_distance(camera_coords: tuple, user_coords: tuple) -> float:
    """Calculate geodesic distance in kilometers between two GPS coordinates.

    Uses `geopy.geodesic` when available; otherwise falls back to a haversine
    implementation so unit tests can run in environments without geopy.
    """
    if not camera_coords or not user_coords:
        raise ValueError("Both camera_coords and user_coords must be provided.")

    try:
        if geodesic is not None:
            return geodesic(camera_coords, user_coords).kilometers
        return _haversine_km(camera_coords, user_coords)
    except Exception as exc:
        raise RuntimeError(f"Failed to calculate distance: {exc}") from exc


def evaluate_risk(animal_name: str, distance_km: float) -> dict:
    """Evaluate intrusion risk based on animal type and distance."""
    if distance_km is None:
        raise ValueError("distance_km must be provided for risk evaluation.")

    normalized_name = animal_name.lower().strip() if animal_name else ""
    is_dangerous = normalized_name in DANGEROUS_ANIMALS

    if is_dangerous and distance_km <= 5.0:
        return {
            "risk_level": "HIGH",
            "reason": f"Dangerous animal '{animal_name}' detected within {distance_km:.2f} km.",
        }

    if distance_km <= 1.0:
        return {
            "risk_level": "HIGH",
            "reason": f"Animal '{animal_name}' detected very close at {distance_km:.2f} km.",
        }

    if is_dangerous and distance_km > 5.0:
        return {
            "risk_level": "LOW",
            "reason": f"Dangerous animal '{animal_name}' detected beyond the high-risk threshold ({distance_km:.2f} km).",
        }

    return {
        "risk_level": "LOW",
        "reason": f"Non-dangerous animal '{animal_name}' detected at a safe distance ({distance_km:.2f} km).",
    }
