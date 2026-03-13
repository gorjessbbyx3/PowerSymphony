"""REST API for AI workers to control the browser via the extension."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.routes.browser_agent import send_browser_command, get_connected_sessions

router = APIRouter(prefix="/api/browser", tags=["browser"])


class BrowserCommandRequest(BaseModel):
    session_id: Optional[str] = None
    timeout: float = 30.0


class OpenTabRequest(BrowserCommandRequest):
    url: str
    active: bool = True


class NavigateRequest(BrowserCommandRequest):
    url: str
    tab_id: Optional[int] = None


class ClickRequest(BrowserCommandRequest):
    selector: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    tab_id: Optional[int] = None


class TypeRequest(BrowserCommandRequest):
    text: str
    selector: Optional[str] = None
    clear: bool = False
    tab_id: Optional[int] = None


class ScrollRequest(BrowserCommandRequest):
    selector: Optional[str] = None
    x: float = 0
    y: float = 300
    tab_id: Optional[int] = None


class SelectorRequest(BrowserCommandRequest):
    selector: str
    tab_id: Optional[int] = None
    timeout: float = 10.0


class FillFormRequest(BrowserCommandRequest):
    fields: Dict[str, str]
    tab_id: Optional[int] = None


class EvalRequest(BrowserCommandRequest):
    code: str
    tab_id: Optional[int] = None


class ScreenshotRequest(BrowserCommandRequest):
    tab_id: Optional[int] = None


@router.get("/sessions")
async def list_sessions() -> Dict[str, Any]:
    """List all connected browser extension sessions."""
    sessions = get_connected_sessions()
    return {"sessions": sessions, "count": len(sessions)}


@router.post("/screenshot")
async def take_screenshot(req: ScreenshotRequest) -> Dict[str, Any]:
    """Take a screenshot of the current or specified tab."""
    try:
        result = await send_browser_command("screenshot", {"tab_id": req.tab_id}, req.session_id, req.timeout)
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/open-tab")
async def open_tab(req: OpenTabRequest) -> Dict[str, Any]:
    """Open a new browser tab at the given URL."""
    try:
        result = await send_browser_command("open_tab", {"url": req.url, "active": req.active}, req.session_id, req.timeout)
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/navigate")
async def navigate(req: NavigateRequest) -> Dict[str, Any]:
    """Navigate a tab to a URL and wait for it to load."""
    try:
        params: Dict[str, Any] = {"url": req.url}
        if req.tab_id is not None:
            params["tab_id"] = req.tab_id
        result = await send_browser_command("navigate", params, req.session_id, req.timeout)
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/click")
async def click(req: ClickRequest) -> Dict[str, Any]:
    """Click an element by CSS selector or (x, y) coordinates."""
    try:
        params: Dict[str, Any] = {}
        if req.selector:
            params["selector"] = req.selector
        if req.x is not None:
            params["x"] = req.x
        if req.y is not None:
            params["y"] = req.y
        if req.tab_id is not None:
            params["tab_id"] = req.tab_id
        result = await send_browser_command("click", params, req.session_id, req.timeout)
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/type")
async def type_text(req: TypeRequest) -> Dict[str, Any]:
    """Type text into a focused or selected element."""
    try:
        params: Dict[str, Any] = {"text": req.text, "clear": req.clear}
        if req.selector:
            params["selector"] = req.selector
        if req.tab_id is not None:
            params["tab_id"] = req.tab_id
        result = await send_browser_command("type", params, req.session_id, req.timeout)
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/scroll")
async def scroll(req: ScrollRequest) -> Dict[str, Any]:
    """Scroll a page or element."""
    try:
        params: Dict[str, Any] = {"x": req.x, "y": req.y}
        if req.selector:
            params["selector"] = req.selector
        if req.tab_id is not None:
            params["tab_id"] = req.tab_id
        result = await send_browser_command("scroll", params, req.session_id, req.timeout)
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/wait-for-selector")
async def wait_for_selector(req: SelectorRequest) -> Dict[str, Any]:
    """Wait for a CSS selector to appear in the DOM."""
    try:
        params: Dict[str, Any] = {"selector": req.selector, "timeout": req.timeout * 1000}
        if req.tab_id is not None:
            params["tab_id"] = req.tab_id
        result = await send_browser_command("wait_for_selector", params, req.session_id, req.timeout + 5)
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/get-element-text")
async def get_element_text(req: SelectorRequest) -> Dict[str, Any]:
    """Get the text content of an element."""
    try:
        params: Dict[str, Any] = {"selector": req.selector}
        if req.tab_id is not None:
            params["tab_id"] = req.tab_id
        result = await send_browser_command("get_element_text", params, req.session_id, req.timeout)
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/fill-form")
async def fill_form(req: FillFormRequest) -> Dict[str, Any]:
    """Fill multiple form fields at once using CSS selectors."""
    try:
        params: Dict[str, Any] = {"fields": req.fields}
        if req.tab_id is not None:
            params["tab_id"] = req.tab_id
        result = await send_browser_command("fill_form", params, req.session_id, req.timeout)
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/get-page-content")
async def get_page_content(req: BrowserCommandRequest) -> Dict[str, Any]:
    """Get the full text/HTML content of the current page."""
    try:
        result = await send_browser_command("get_page_content", {}, req.session_id, req.timeout)
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/tabs")
async def get_tabs(session_id: Optional[str] = None) -> Dict[str, Any]:
    """List all open browser tabs."""
    try:
        result = await send_browser_command("get_tabs", {}, session_id, 10.0)
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/eval")
async def eval_js(req: EvalRequest) -> Dict[str, Any]:
    """Evaluate arbitrary JavaScript in the browser tab."""
    try:
        params: Dict[str, Any] = {"code": req.code}
        if req.tab_id is not None:
            params["tab_id"] = req.tab_id
        result = await send_browser_command("eval", params, req.session_id, req.timeout)
        return {"ok": True, "result": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
