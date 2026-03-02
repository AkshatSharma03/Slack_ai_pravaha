"""Utility tools: date/time, weather, URL content fetcher."""
import requests
from datetime import datetime

try:
    import pytz
    _HAS_PYTZ = True
except ImportError:
    _HAS_PYTZ = False


def get_current_datetime(timezone: str = "UTC") -> str:
    """Return the current date and time in the requested timezone."""
    try:
        if _HAS_PYTZ:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            return now.strftime(
                f"Current datetime in {timezone}: %A, %B %d, %Y at %H:%M:%S %Z (UTC%z)"
            )
        from datetime import timezone as dt_tz
        now = datetime.now(dt_tz.utc)
        return f"Current UTC time: {now.strftime('%A, %B %d, %Y at %H:%M:%S UTC')}"
    except Exception:
        from datetime import timezone as dt_tz
        now = datetime.now(dt_tz.utc)
        return (
            f"Unknown timezone '{timezone}'. "
            f"UTC: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )


def get_weather(location: str) -> str:
    """Get current weather for a location using wttr.in (no API key needed)."""
    try:
        encoded = requests.utils.quote(location)
        r = requests.get(
            f"https://wttr.in/{encoded}?format=j1",
            timeout=10,
            headers={"User-Agent": "PravahaBot/2.0"},
        )
        if r.status_code != 200:
            return f"Weather data unavailable for: {location}"

        data = r.json()
        current = data.get("current_condition", [{}])[0]
        nearest = data.get("nearest_area", [{}])[0]

        area = nearest.get("areaName", [{}])[0].get("value", location)
        country = nearest.get("country", [{}])[0].get("value", "")
        location_str = f"{area}, {country}" if country else area

        desc = current.get("weatherDesc", [{}])[0].get("value", "?")
        temp_c = current.get("temp_C", "?")
        temp_f = current.get("temp_F", "?")
        feels_c = current.get("FeelsLikeC", "?")
        humidity = current.get("humidity", "?")
        wind_kmph = current.get("windspeedKmph", "?")
        visibility = current.get("visibility", "?")

        return (
            f"🌍 *Weather in {location_str}*\n"
            f"• Condition: {desc}\n"
            f"• Temperature: {temp_c}°C / {temp_f}°F  (feels like {feels_c}°C)\n"
            f"• Humidity: {humidity}%\n"
            f"• Wind: {wind_kmph} km/h\n"
            f"• Visibility: {visibility} km"
        )
    except Exception as e:
        return f"Weather fetch failed: {str(e)}"


def fetch_url_content(url: str) -> str:
    """Download and extract readable text from a URL."""
    try:
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Strip boilerplate
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()

        # Prefer semantic content elements
        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find(id="content")
            or soup.find("div", class_=lambda c: c and "content" in c.lower())
            or soup.body
            or soup
        )

        lines = [
            line.strip()
            for line in main.get_text(separator="\n").split("\n")
            if line.strip()
        ]
        text = "\n".join(lines)

        if len(text) > 5000:
            text = text[:5000] + "\n\n[...content truncated at 5000 chars]"

        return f"Content from {url}:\n\n{text}" if text else f"No readable content at {url}"
    except Exception as e:
        return f"Failed to fetch {url}: {str(e)}"
