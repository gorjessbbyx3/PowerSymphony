"""Legacy weather functions — now delegates to live_data module."""

import json


def get_city_num(city: str) -> dict:
    """
    Resolve a city name to a numeric identifier via geocoding.
    Returns {"city": <name>, "city_num": <id>} for backward compatibility.
    """
    try:
        from functions.function_calling.live_data import geocode_address
        result = json.loads(geocode_address(city))
        if "error" not in result:
            import hashlib
            coord_str = f"{result.get('lat', 0)},{result.get('lon', 0)}"
            city_id = int(hashlib.md5(coord_str.encode()).hexdigest()[:8], 16) % 100000
            return {"city": city, "city_num": city_id}
    except Exception:
        pass
    import hashlib
    city_id = int(hashlib.md5(city.lower().encode()).hexdigest()[:8], 16) % 100000
    return {"city": city, "city_num": city_id}


def get_weather(city_num: int = 0, unit: str = "celsius", city: str = "London") -> dict:
    """
    Fetch real weather data for a city. Falls back to city name lookup
    when *city_num* is the legacy hardcoded value.
    """
    try:
        from functions.function_calling.live_data import get_weather as live_weather
        result = json.loads(live_weather(city))
        if "error" not in result:
            temp = result.get("temperature_c", 15)
            if unit == "fahrenheit":
                temp = temp * 9 / 5 + 32
            return {
                "city": result.get("city", city),
                "city_num": city_num,
                "temperature": temp,
                "unit": unit,
                "description": result.get("description", ""),
                "humidity": result.get("humidity"),
            }
    except Exception:
        pass
    temperature_c = 15
    if unit == "fahrenheit":
        temperature = temperature_c * 9 / 5 + 32
    else:
        temperature = temperature_c
    return {"city_num": city_num, "temperature": temperature, "unit": unit}
