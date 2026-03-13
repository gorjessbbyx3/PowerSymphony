"""Live External Data — real-time API tool functions.

Pulls live data from public APIs:
- Weather: OpenWeatherMap (requires OPENWEATHERMAP_API_KEY)
- Crypto prices: CoinGecko (no API key needed)
- News: NewsAPI (requires NEWSAPI_KEY)
- Geocoding: Nominatim/OpenStreetMap (no API key needed)
- Stock data: Yahoo Finance compatible (no API key needed)
"""

import json
import os
import urllib.request
import urllib.parse
from typing import Any, Dict, Optional


def _http_get(url: str, headers: Optional[Dict] = None) -> Any:
    req = urllib.request.Request(url, headers=headers or {
        "User-Agent": "PowerSymphony/1.0 (workflow automation)"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        return {"error": str(exc)}


def get_weather(city: str, units: str = "metric") -> str:
    """
    Get current weather for a city using OpenWeatherMap.
    Requires OPENWEATHERMAP_API_KEY environment variable.

    Args:
        city (str): City name, e.g. "Honolulu" or "London,UK".
        units (str): Temperature units: metric (°C), imperial (°F), or standard (K).

    Returns:
        str: JSON with temperature, feels_like, humidity, wind_speed, description, city, country.
    """
    api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return json.dumps({"error": "OPENWEATHERMAP_API_KEY is not set. Add it as an environment variable."})
    q = urllib.parse.quote(city)
    url = f"https://api.openweathermap.org/data/2.5/weather?q={q}&units={units}&appid={api_key}"
    data = _http_get(url)
    if "error" in data or "cod" in data and data["cod"] != 200:
        return json.dumps({"error": data.get("message", str(data))})
    return json.dumps({
        "city": data.get("name"),
        "country": data.get("sys", {}).get("country"),
        "temperature": data.get("main", {}).get("temp"),
        "feels_like": data.get("main", {}).get("feels_like"),
        "humidity": data.get("main", {}).get("humidity"),
        "wind_speed": data.get("wind", {}).get("speed"),
        "description": data.get("weather", [{}])[0].get("description"),
        "units": units,
    }, indent=2)


def get_weather_forecast(city: str, days: int = 5, units: str = "metric") -> str:
    """
    Get a multi-day weather forecast for a city.
    Requires OPENWEATHERMAP_API_KEY environment variable.

    Args:
        city (str): City name, e.g. "Tokyo".
        days (int): Number of days ahead (1-5). Defaults to 5.
        units (str): metric, imperial, or standard.

    Returns:
        str: JSON array of daily forecast items with date, temp, and description.
    """
    api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return json.dumps({"error": "OPENWEATHERMAP_API_KEY is not set."})
    q = urllib.parse.quote(city)
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={q}&units={units}&cnt={days * 8}&appid={api_key}"
    data = _http_get(url)
    if "error" in data:
        return json.dumps(data)
    # Group by date and pick noon reading
    seen_dates = {}
    for item in data.get("list", []):
        date = item.get("dt_txt", "")[:10]
        if date and date not in seen_dates:
            seen_dates[date] = {
                "date": date,
                "temp_day": item.get("main", {}).get("temp"),
                "temp_night": item.get("main", {}).get("temp_min"),
                "humidity": item.get("main", {}).get("humidity"),
                "description": item.get("weather", [{}])[0].get("description"),
                "wind_speed": item.get("wind", {}).get("speed"),
            }
    forecast = list(seen_dates.values())[:days]
    return json.dumps({"city": city, "units": units, "forecast": forecast}, indent=2)


def get_crypto_price(coins: str, currency: str = "usd") -> str:
    """
    Get live cryptocurrency prices from CoinGecko (no API key required).

    Args:
        coins (str): Comma-separated CoinGecko coin IDs, e.g.
                     "bitcoin,ethereum,solana" or "bitcoin".
        currency (str): Fiat currency to quote in, e.g. "usd", "eur", "jpy".

    Returns:
        str: JSON object with each coin's price, 24h change, market cap, and volume.
    """
    ids = urllib.parse.quote(coins.lower().replace(" ", ""))
    url = (f"https://api.coingecko.com/api/v3/simple/price"
           f"?ids={ids}&vs_currencies={currency}"
           f"&include_market_cap=true&include_24hr_vol=true&include_24hr_change=true")
    data = _http_get(url)
    if "error" in data:
        return json.dumps(data)
    result = {}
    for coin_id, stats in data.items():
        result[coin_id] = {
            "price": stats.get(currency),
            "market_cap": stats.get(f"{currency}_market_cap"),
            "volume_24h": stats.get(f"{currency}_24h_vol"),
            "change_24h_pct": stats.get(f"{currency}_24h_change"),
            "currency": currency.upper(),
        }
    return json.dumps(result, indent=2)


def get_crypto_trending() -> str:
    """
    Get the top 7 trending cryptocurrencies on CoinGecko right now (no API key required).

    Returns:
        str: JSON array with name, symbol, market_cap_rank, and price_btc for each coin.
    """
    data = _http_get("https://api.coingecko.com/api/v3/search/trending")
    if "error" in data:
        return json.dumps(data)
    coins = data.get("coins", [])
    result = [
        {
            "name": c.get("item", {}).get("name"),
            "symbol": c.get("item", {}).get("symbol"),
            "market_cap_rank": c.get("item", {}).get("market_cap_rank"),
            "price_btc": c.get("item", {}).get("price_btc"),
            "thumb": c.get("item", {}).get("thumb"),
        }
        for c in coins
    ]
    return json.dumps(result, indent=2)


def get_news_headlines(query: str = "", category: str = "", country: str = "us",
                       max_results: int = 5) -> str:
    """
    Get live news headlines. Requires NEWSAPI_KEY environment variable.
    Free tier available at newsapi.org.

    Args:
        query (str): Search keywords, e.g. "AI startup funding". Empty for top headlines.
        category (str): Category filter: business, entertainment, health, science, sports, technology.
        country (str): 2-letter country code for top headlines, e.g. "us", "gb". Defaults to "us".
        max_results (int): Number of articles to return (1-10). Defaults to 5.

    Returns:
        str: JSON array with title, description, source, url, and published_at.
    """
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        return json.dumps({"error": "NEWSAPI_KEY is not set. Get a free key at newsapi.org."})
    max_results = max(1, min(int(max_results), 10))
    if query:
        q = urllib.parse.quote(query)
        url = f"https://newsapi.org/v2/everything?q={q}&pageSize={max_results}&sortBy=publishedAt&apiKey={api_key}"
    else:
        params = f"country={country}&pageSize={max_results}"
        if category:
            params += f"&category={category}"
        url = f"https://newsapi.org/v2/top-headlines?{params}&apiKey={api_key}"
    data = _http_get(url)
    if "error" in data or data.get("status") == "error":
        return json.dumps({"error": data.get("message", str(data))})
    articles = [
        {
            "title": a.get("title"),
            "description": a.get("description"),
            "source": a.get("source", {}).get("name"),
            "url": a.get("url"),
            "published_at": a.get("publishedAt"),
        }
        for a in data.get("articles", [])
    ]
    return json.dumps(articles, indent=2)


def geocode_location(address: str) -> str:
    """
    Convert an address or place name to geographic coordinates (lat/lon).
    Uses OpenStreetMap Nominatim — no API key required.

    Args:
        address (str): Address or place name, e.g. "Diamond Head, Honolulu, Hawaii".

    Returns:
        str: JSON with latitude, longitude, display_name, type, and bounding_box.
    """
    q = urllib.parse.quote(address)
    url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=3"
    data = _http_get(url, headers={"User-Agent": "PowerSymphony/1.0"})
    if "error" in data:
        return json.dumps(data)
    if not data:
        return json.dumps({"error": f"No results found for: {address}"})
    results = [
        {
            "latitude": float(item.get("lat", 0)),
            "longitude": float(item.get("lon", 0)),
            "display_name": item.get("display_name"),
            "type": item.get("type"),
            "importance": item.get("importance"),
        }
        for item in data[:3]
    ]
    return json.dumps({"query": address, "results": results}, indent=2)


def get_stock_quote(symbol: str) -> str:
    """
    Get a stock quote via Yahoo Finance (no API key required).

    Args:
        symbol (str): Stock ticker symbol, e.g. "AAPL", "GOOGL", "TSLA".

    Returns:
        str: JSON with symbol, price, change, change_percent, volume, market_cap.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}?interval=1d&range=1d"
    data = _http_get(url, headers={"User-Agent": "Mozilla/5.0"})
    if "error" in data:
        return json.dumps(data)
    try:
        meta = data["chart"]["result"][0]["meta"]
        return json.dumps({
            "symbol": meta.get("symbol"),
            "price": meta.get("regularMarketPrice"),
            "previous_close": meta.get("previousClose"),
            "change": round((meta.get("regularMarketPrice", 0) - meta.get("previousClose", 0)), 4),
            "change_pct": round(((meta.get("regularMarketPrice", 0) - meta.get("previousClose", 0)) / max(meta.get("previousClose", 1), 0.01)) * 100, 2),
            "volume": meta.get("regularMarketVolume"),
            "currency": meta.get("currency"),
            "exchange": meta.get("exchangeName"),
        }, indent=2)
    except (KeyError, IndexError, TypeError) as e:
        return json.dumps({"error": f"Could not parse quote for {symbol}: {e}"})
