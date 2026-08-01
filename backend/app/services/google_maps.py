import httpx

from app.core.config import get_settings


class GoogleMapsClient:
    """
    Google Maps Platform client for TrafficSMS.

    Responsibilities:
    - Geocoding
    - Routes API
    - Future Places API
    """

    def __init__(self):
        settings = get_settings()

        self.api_key = settings.google_maps_api_key
        self.timeout = settings.google_maps_timeout_seconds

        self.geocode_url = (
            "https://maps.googleapis.com/maps/api/geocode/json"
        )

        self.routes_url = (
            "https://routes.googleapis.com/directions/v2:computeRoutes"
        )

    async def geocode(self, location: str) -> dict:
        """
        Convert a city, ZIP code, highway, or place into coordinates.
        """

        print(f"GEOCODING: {repr(location)}", flush=True)

        params = {
            "address": location,
            "key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.geocode_url,
                params=params,
            )

        response.raise_for_status()

        data = response.json()

        print("=" * 80, flush=True)
        print("GEOCODE REQUEST:", location, flush=True)
        print("HTTP STATUS:", response.status_code, flush=True)
        print("GEOCODE RESPONSE:", data, flush=True)
        print("=" * 80, flush=True)

        if data["status"] != "OK":
            raise ValueError(
                f"Google Geocoding failed:\n{data}"
        )

        result = data["results"][0]

        return {
            "formatted_address": result["formatted_address"],
            "latitude": result["geometry"]["location"]["lat"],
            "longitude": result["geometry"]["location"]["lng"],
            "place_id": result["place_id"],
        }

    async def compute_route(
        self,
        origin: str,
        destination: str,
    ) -> dict:
        """
        Compute a driving route using Google's Routes API.
        """

        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "routes.duration,"
                "routes.staticDuration,"
                "routes.distanceMeters,"
                "routes.polyline.encodedPolyline"
            ),
        }

        body = {
            "origin": {
                "address": origin,
            },
            "destination": {
                "address": destination,
            },
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.routes_url,
                headers=headers,
                json=body,
            )

        print("=" * 80, flush=True)
        print("GOOGLE ROUTES STATUS:", response.status_code, flush=True)
        print("GOOGLE ROUTES HEADERS:", dict(response.headers), flush=True)
        print("GOOGLE ROUTES BODY:", response.text, flush=True)
        print("=" * 80, flush=True)

        response.raise_for_status()

        data = response.json()

        print(f"GEOCODE RESPONSE: {data}", flush=True)

        if "routes" not in data or not data["routes"]:
            raise ValueError("No routes returned.")

        route = data["routes"][0]

        distance_meters = route["distanceMeters"]

        travel_seconds = int(route["duration"][:-1])

        normal_seconds = int(route["staticDuration"][:-1])

        delay_seconds = max(
            0,
            travel_seconds - normal_seconds,
        )

        distance_miles = distance_meters / 1609.344

        travel_minutes = round(travel_seconds / 60)

        normal_minutes = round(normal_seconds / 60)

        delay_minutes = round(delay_seconds / 60)

        average_speed = 0

        if travel_seconds > 0:
            average_speed = round(
                distance_miles / (travel_seconds / 3600)
            )

        return {
            "distance_miles": round(distance_miles, 1),
            "travel_minutes": travel_minutes,
            "normal_minutes": normal_minutes,
            "delay_minutes": delay_minutes,
            "average_speed_mph": average_speed,
            "polyline": route["polyline"]["encodedPolyline"],
        }

google_maps = GoogleMapsClient()