import json
import logging
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("healthcare")

# OpenStreetMap services.
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Always identify the application when using Nominatim.
USER_AGENT = "Kural-Health-Access-Voice-Agent/1.0"

REQUEST_TIMEOUT = 10
SEARCH_RADIUS_METERS = 10000


def _http_get(url: str) -> bytes:
    """Make a GET request with a timeout and application User-Agent."""

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return response.read()


def _http_post(url: str, data: str) -> bytes:
    """Make a POST request with a timeout and application User-Agent."""

    request = Request(
        url,
        data=data.encode("utf-8"),
        method="POST",
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return response.read()


def _geocode_location(location: str) -> dict:
    """
    Convert a human-readable location into latitude and longitude
    using OpenStreetMap Nominatim.
    """

    params = (
        f"?q={quote(location)}"
        f"&format=json"
        f"&limit=1"
        f"&countrycodes=in"
    )

    try:
        response = _http_get(NOMINATIM_URL + params)
        results = json.loads(response.decode("utf-8"))

    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.exception("Geocoding failed for location=%s", location)

        return {
            "success": False,
            "error": "The location service is temporarily unavailable.",
        }

    if not results:
        return {
            "success": False,
            "error": f"I could not find the location '{location}'.",
        }

    result = results[0]

    try:
        latitude = float(result["lat"])
        longitude = float(result["lon"])
    except (KeyError, ValueError):
        return {
            "success": False,
            "error": "The location service returned an invalid result.",
        }

    return {
        "success": True,
        "latitude": latitude,
        "longitude": longitude,
        "display_name": result.get("display_name", location),
    }


def _build_overpass_query(
    latitude: float,
    longitude: float,
    facility_type: str,
) -> str:
    """
    Build an Overpass query for healthcare facilities near a location.
    """

    if facility_type == "hospital":
        filters = """
            nwr(around:10000,LATITUDE,LONGITUDE)["amenity"="hospital"];
        """

    elif facility_type == "clinic":
        filters = """
            nwr(around:10000,LATITUDE,LONGITUDE)["amenity"="clinic"];
            nwr(around:10000,LATITUDE,LONGITUDE)["healthcare"="clinic"];
            nwr(around:10000,LATITUDE,LONGITUDE)["amenity"="doctors"];
        """

    else:
        # "any" is useful for general questions such as
        # "find a nearby health facility".
        filters = """
            nwr(around:10000,LATITUDE,LONGITUDE)["amenity"="hospital"];
            nwr(around:10000,LATITUDE,LONGITUDE)["amenity"="clinic"];
            nwr(around:10000,LATITUDE,LONGITUDE)["amenity"="doctors"];
            nwr(around:10000,LATITUDE,LONGITUDE)["healthcare"];
        """

    query = f"""
    [out:json][timeout:15];

    (
        {filters}
    );

    out center tags;
    """

    return (
        query
        .replace("LATITUDE", str(latitude))
        .replace("LONGITUDE", str(longitude))
    )


def _facility_name(tags: dict) -> str:
    """Get the most useful facility name available."""

    name = tags.get("name")

    if name:
        return name

    official_name = tags.get("official_name")

    if official_name:
        return official_name

    return "Unnamed healthcare facility"


def _facility_type(tags: dict) -> str:
    """Convert OpenStreetMap tags into a simple facility type."""

    amenity = tags.get("amenity", "").lower()
    healthcare = tags.get("healthcare", "").lower()

    if amenity == "hospital":
        return "Hospital"

    if amenity == "clinic" or healthcare == "clinic":
        return "Clinic"

    if amenity == "doctors":
        return "Doctor's facility"

    if healthcare:
        return healthcare.replace("_", " ").title()

    return "Healthcare facility"


def _calculate_distance_km(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calculate approximate straight-line distance using the Haversine formula.
    """

    import math

    earth_radius_km = 6371.0

    lat1 = math.radians(latitude_1)
    lat2 = math.radians(latitude_2)

    delta_lat = math.radians(latitude_2 - latitude_1)
    delta_lon = math.radians(longitude_2 - longitude_1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius_km * c


def find_healthcare_facilities(
    location: str,
    facility_type: str = "any",
    limit: int = 3,
) -> dict:
    """
    Find nearby healthcare facilities using OpenStreetMap data.

    Args:
        location: City, town, district, or locality.
        facility_type: "hospital", "clinic", or "any".
        limit: Maximum number of facilities to return.
    """

    if not location or not location.strip():
        return {
            "success": False,
            "error": "A city or locality is required.",
        }

    location = location.strip()
    facility_type = facility_type.lower().strip()

    if facility_type not in {"hospital", "clinic", "any"}:
        facility_type = "any"

    limit = max(1, min(limit, 5))

    logger.info(
        "Healthcare lookup: location=%s, type=%s",
        location,
        facility_type,
    )

    # Step 1: Convert location into coordinates.
    geocoded = _geocode_location(location)

    if not geocoded["success"]:
        return geocoded

    latitude = geocoded["latitude"]
    longitude = geocoded["longitude"]

    # Step 2: Search OpenStreetMap for facilities.
    query = _build_overpass_query(
        latitude,
        longitude,
        facility_type,
    )

    try:
        response = _http_post(
            OVERPASS_URL,
            "data=" + quote(query),
        )

        data = json.loads(response.decode("utf-8"))

    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.exception(
            "Healthcare facility lookup failed for location=%s",
            location,
        )

        return {
            "success": False,
            "error": (
                "The healthcare facility service is temporarily "
                "unavailable. I cannot provide a reliable facility "
                "result right now."
            ),
        }

    elements = data.get("elements", [])

    facilities = []

    for element in elements:
        tags = element.get("tags", {})

        if not tags:
            continue

        # Nodes have lat/lon directly. Ways/relations usually have a center.
        facility_lat = element.get("lat")
        facility_lon = element.get("lon")

        center = element.get("center", {})

        if facility_lat is None:
            facility_lat = center.get("lat")

        if facility_lon is None:
            facility_lon = center.get("lon")

        if facility_lat is None or facility_lon is None:
            continue

        try:
            facility_lat = float(facility_lat)
            facility_lon = float(facility_lon)
        except (ValueError, TypeError):
            continue

        distance = _calculate_distance_km(
            latitude,
            longitude,
            facility_lat,
            facility_lon,
        )

        address_parts = []

        for key in (
            "addr:housenumber",
            "addr:street",
            "addr:suburb",
            "addr:city",
        ):
            value = tags.get(key)

            if value:
                address_parts.append(value)

        address = ", ".join(address_parts)

        facilities.append(
            {
                "name": _facility_name(tags),
                "type": _facility_type(tags),
                "distance_km": round(distance, 2),
                "address": address,
                "latitude": facility_lat,
                "longitude": facility_lon,
            }
        )

    # Remove duplicates based on name + coordinates.
    unique_facilities = {}

    for facility in facilities:
        key = (
            facility["name"].lower(),
            round(facility["latitude"], 5),
            round(facility["longitude"], 5),
        )

        unique_facilities[key] = facility

    facilities = list(unique_facilities.values())

    facilities.sort(key=lambda item: item["distance_km"])

    facilities = facilities[:limit]

    retrieved_at = datetime.now(timezone.utc).isoformat()

    if not facilities:
        return {
            "success": True,
            "found": False,
            "location": location,
            "message": (
                "No matching healthcare facilities were found "
                "within approximately 10 kilometres of the requested location."
            ),
            "source": "OpenStreetMap",
            "retrieved_at": retrieved_at,
        }

    return {
        "success": True,
        "found": True,
        "location": location,
        "facilities": facilities,
        "source": "OpenStreetMap",
        "retrieved_at": retrieved_at,
        "note": (
            "Facility information comes from OpenStreetMap and "
            "may not always be complete or current."
        ),
    }