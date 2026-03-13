"""REST API for web scraping — usable from the frontend or external tools."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

router = APIRouter(prefix="/api/scrape", tags=["scraping"])


class ScrapeRequest(BaseModel):
    url: str
    selector: str = ""
    include_links: bool = False


class BatchScrapeRequest(BaseModel):
    urls: List[str]
    selector: str = ""


class TableRequest(BaseModel):
    url: str
    table_index: int = 0


class ExtractRequest(BaseModel):
    url: str
    fields: Dict[str, str]


class LinksRequest(BaseModel):
    url: str
    base_url: str = ""


@router.post("/url")
async def scrape_url_endpoint(req: ScrapeRequest) -> Dict[str, Any]:
    """
    Scrape a single URL and return the page title and main text.
    Optionally restrict extraction to a CSS selector.
    """
    try:
        from functions.function_calling.scraping import scrape_url
        content = scrape_url(req.url, selector=req.selector, include_links=req.include_links)
        return {"ok": True, "url": req.url, "content": content}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/links")
async def scrape_links_endpoint(req: LinksRequest) -> Dict[str, Any]:
    """Extract all hyperlinks from a web page."""
    try:
        import json
        from functions.function_calling.scraping import scrape_links
        result = scrape_links(req.url, base_url=req.base_url)
        return {"ok": True, "url": req.url, "links": json.loads(result)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/table")
async def scrape_table_endpoint(req: TableRequest) -> Dict[str, Any]:
    """Extract an HTML table from a web page and return it as CSV text."""
    try:
        from functions.function_calling.scraping import scrape_table
        csv_text = scrape_table(req.url, table_index=req.table_index)
        return {"ok": True, "url": req.url, "table_index": req.table_index, "csv": csv_text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/extract")
async def extract_structured_data_endpoint(req: ExtractRequest) -> Dict[str, Any]:
    """Extract structured data from a page using CSS selectors."""
    try:
        import json
        from functions.function_calling.scraping import extract_structured_data
        fields_json = json.dumps(req.fields)
        result = extract_structured_data(req.url, fields=fields_json)
        return {"ok": True, "url": req.url, "data": json.loads(result)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/batch")
async def batch_scrape_endpoint(req: BatchScrapeRequest) -> Dict[str, Any]:
    """Scrape multiple URLs concurrently and return summaries for each."""
    try:
        import json
        from functions.function_calling.scraping import batch_scrape
        urls_json = json.dumps(req.urls)
        result = batch_scrape(urls_json, selector=req.selector)
        return {"ok": True, "results": json.loads(result)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
