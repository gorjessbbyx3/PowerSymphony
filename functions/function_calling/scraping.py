"""Web scraping and data extraction tool functions for workflow agents."""

import json
import os
from typing import Any, Dict, List, Optional


def scrape_url(url: str, selector: str = "", include_links: bool = False) -> str:
    """
    Scrape a web page and return its title, main text content, and optionally all links.

    Args:
        url (str): The URL to scrape.
        selector (str): Optional CSS selector to extract specific element text. Empty = full page.
        include_links (bool): If True, also return all hyperlinks found on the page.

    Returns:
        str: A formatted string with the page title, extracted text, and optionally links.
    """
    import requests
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        return f"Error fetching {url}: {exc}"

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove noise
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else "(no title)"

    if selector:
        elements = soup.select(selector)
        if not elements:
            text = f"(No elements matched selector: {selector})"
        else:
            text = "\n\n".join(el.get_text(separator=" ", strip=True) for el in elements)
    else:
        # Prefer <main> or <article>, fallback to <body>
        content_tag = soup.find("main") or soup.find("article") or soup.body
        text = content_tag.get_text(separator="\n", strip=True) if content_tag else ""
        # Collapse excessive blank lines
        lines = [l for l in text.splitlines() if l.strip()]
        text = "\n".join(lines)

    result = f"# {title}\n\n{text[:8000]}"

    if include_links:
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            label = a.get_text(strip=True) or href
            if href.startswith("http"):
                links.append(f"- [{label}]({href})")
        if links:
            result += "\n\n## Links\n" + "\n".join(links[:50])

    return result


def scrape_links(url: str, base_url: str = "") -> str:
    """
    Extract all hyperlinks from a web page.

    Args:
        url (str): The URL to scrape links from.
        base_url (str): If provided, resolve relative URLs against this base. Defaults to the page URL.

    Returns:
        str: JSON array of objects with 'text' and 'href' fields.
    """
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlparse

    headers = {"User-Agent": "Mozilla/5.0 PowerSymphony-Scraper/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        return json.dumps({"error": str(exc)})

    soup = BeautifulSoup(resp.text, "html.parser")
    base = base_url or url
    links: List[Dict[str, str]] = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        resolved = urljoin(base, href)
        if resolved not in seen and urlparse(resolved).scheme in ("http", "https"):
            seen.add(resolved)
            links.append({"text": a.get_text(strip=True), "href": resolved})

    return json.dumps(links[:200], ensure_ascii=False, indent=2)


def scrape_table(url: str, table_index: int = 0) -> str:
    """
    Extract a specific HTML table from a web page and return it as CSV-formatted text.

    Args:
        url (str): The URL containing the table.
        table_index (int): Which table to extract (0-based index). Defaults to 0 (first table).

    Returns:
        str: The table data as CSV text, or an error message.
    """
    import requests
    from bs4 import BeautifulSoup
    import csv
    import io

    headers = {"User-Agent": "Mozilla/5.0 PowerSymphony-Scraper/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        return f"Error fetching {url}: {exc}"

    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table")

    if not tables:
        return "No tables found on the page."
    if table_index >= len(tables):
        return f"Table index {table_index} out of range. Found {len(tables)} table(s)."

    table = tables[table_index]
    rows = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(separator=" ", strip=True) for td in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    return buf.getvalue()


def extract_structured_data(url: str, fields: str) -> str:
    """
    Extract structured data from a web page using CSS selectors.

    Args:
        url (str): The URL to scrape.
        fields (str): JSON object mapping field names to CSS selectors, e.g.
                      '{"title": "h1", "price": ".price", "description": ".desc"}' .

    Returns:
        str: JSON object with the extracted values per field.
    """
    import requests
    from bs4 import BeautifulSoup

    try:
        field_map: Dict[str, str] = json.loads(fields)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid fields JSON: {exc}"})

    headers = {"User-Agent": "Mozilla/5.0 PowerSymphony-Scraper/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        return json.dumps({"error": str(exc)})

    soup = BeautifulSoup(resp.text, "html.parser")
    result: Dict[str, Any] = {}

    for field_name, selector in field_map.items():
        elements = soup.select(selector)
        if not elements:
            result[field_name] = None
        elif len(elements) == 1:
            result[field_name] = elements[0].get_text(strip=True)
        else:
            result[field_name] = [el.get_text(strip=True) for el in elements]

    return json.dumps(result, ensure_ascii=False, indent=2)


def batch_scrape(urls_json: str, selector: str = "") -> str:
    """
    Scrape multiple URLs concurrently and return a summary of each page.

    Args:
        urls_json (str): JSON array of URLs to scrape, e.g. '["https://a.com", "https://b.com"]'.
        selector (str): Optional CSS selector applied to every page. Empty = full page text.

    Returns:
        str: JSON array of objects with 'url', 'title', 'text', and 'error' fields.
    """
    import requests
    from bs4 import BeautifulSoup
    from concurrent.futures import ThreadPoolExecutor, as_completed

    try:
        urls: List[str] = json.loads(urls_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid urls JSON: {exc}"})

    if not isinstance(urls, list):
        return json.dumps({"error": "urls_json must be a JSON array"})

    urls = urls[:20]  # cap at 20 to avoid abuse

    headers = {"User-Agent": "Mozilla/5.0 PowerSymphony-Scraper/1.0"}

    def _scrape_one(url: str) -> Dict[str, Any]:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            title = soup.title.get_text(strip=True) if soup.title else ""
            if selector:
                elements = soup.select(selector)
                text = "\n".join(el.get_text(strip=True) for el in elements)
            else:
                body = soup.body
                text = body.get_text(separator="\n", strip=True) if body else ""
            return {"url": url, "title": title, "text": text[:3000], "error": None}
        except Exception as exc:
            return {"url": url, "title": None, "text": None, "error": str(exc)}

    results = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_scrape_one, u): u for u in urls}
        for fut in as_completed(futures):
            results.append(fut.result())

    return json.dumps(results, ensure_ascii=False, indent=2)
