"""The website: public catalogs, each school's secret staff page, and your owner page.

Public (anyone):      /                   school list
                      /cms-west           catalog (English + Spanish)
                      /qr                 QR codes to show on screen
Staff (secret link):  /upload/cms-west-<token>
You (secret link):    /owner/<token>
"""
from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import pages
import settings
import store
from finder import Finder

log = logging.getLogger("snapsortai.web")

def load_dotenv(path: Path = Path(__file__).resolve().parent / ".env") -> None:
    """Copy KEY=value lines from .env into the environment. A non-empty variable already set wins."""
    if not path.exists():
        log.info("No .env file; using the environment only")
        return
    loaded = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):]
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if not os.environ.get(key.strip(), "").strip():
                os.environ[key.strip()] = value.strip().strip('"').strip("'")
                loaded.append(key.strip())
    log.info("Read .env: %s", ", ".join(loaded) or "nothing new (already set in the environment)")


load_dotenv()
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.state.public_url = ""  # run_demo.py sets this to the Cloudflare address
app.state.finder = None

MESSAGES = {
    "uploaded": "Uploaded. Finding items now.",
    "added": "Added to the public page.",
    "updated": "Done.",
    "new-link": "New upload link made. The old one no longer works; send the new one to the school.",
    "reset": "That school's items were deleted.",
}


def finder() -> Finder:
    if app.state.finder is None:
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        app.state.finder = Finder(key or None, settings.MODEL, settings.GEMINI_TIMEOUT_S)
        log.info("Gemini ready: model %s, key %s, %ds timeout per call", settings.MODEL,
                 "set" if key else "NOT set", settings.GEMINI_TIMEOUT_S)
    return app.state.finder


def base_url(request: Request) -> str:
    return app.state.public_url or str(request.base_url).rstrip("/")


def page(content: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(content, status_code=status)


def not_found() -> HTMLResponse:
    return page(pages.message_page("Not found", "That page doesn't exist, or the link has changed."), 404)


SECRET_PART = re.compile(r"^/(upload/[^/]*-|owner/)[^/-]+")  # greedy: the token is after the LAST "-"


def safe_path(path: str) -> str:
    """The request path with the secret part of upload and owner links hidden."""
    return SECRET_PART.sub(r"/\1***", path)


@app.middleware("http")
async def headers(request: Request, call_next):
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("%s %s crashed", request.method, safe_path(request.url.path))
        raise
    ms = (time.monotonic() - started) * 1000
    level = (logging.ERROR if response.status_code >= 500 else
             logging.INFO if request.method == "POST" else logging.DEBUG)
    log.log(level, "%s %s -> %d (%.0f ms)", request.method, safe_path(request.url.path), response.status_code, ms)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith(("/upload/", "/owner/")):
        response.headers["Referrer-Policy"] = "no-referrer"  # secret links never leak to other sites
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    else:
        response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return not_found()
    return page(pages.message_page("Sorry", str(exc.detail)), exc.status_code)


# ---- public -----------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def home():
    return page(pages.home_page())


@app.get("/qr", response_class=HTMLResponse)
def qr(request: Request):
    return page(pages.qr_page(base_url(request)))


# ---- owner (you) ------------------------------------------------------------
@app.get("/owner/{token}", response_class=HTMLResponse)
def owner(request: Request, token: str, m: str = ""):
    if not store.is_owner(token):
        log.warning("Someone opened an owner link with the wrong token")
        return not_found()
    return page(pages.owner_page(token, base_url(request), MESSAGES.get(m, "")))


@app.post("/owner/{token}/rotate/{school}")
def rotate(token: str, school: str):
    if not store.is_owner(token) or school not in settings.SCHOOLS:
        return not_found()
    store.rotate_link(school)
    return RedirectResponse(f"/owner/{token}?m=new-link", status_code=303)


@app.post("/owner/{token}/reset/{school}")
def reset(token: str, school: str, confirm: str = Form("")):
    if not store.is_owner(token) or school not in settings.SCHOOLS:
        return not_found()
    if confirm == "yes":
        store.reset_school(school)
        return RedirectResponse(f"/owner/{token}?m=reset", status_code=303)
    return RedirectResponse(f"/owner/{token}", status_code=303)


# ---- staff (each school's secret link) ---------------------------------------
@app.get("/upload/{key}", response_class=HTMLResponse)
def staff(key: str, m: str = ""):
    school = store.school_for_key(key)
    if not school:
        log.warning("Someone opened a staff link that doesn't work (wrong or old token)")
        return not_found()
    return page(pages.staff_page(school, key, message=MESSAGES.get(m, "")))


@app.post("/upload/{key}")
async def upload(request: Request, key: str):
    school = store.school_for_key(key)
    if not school:
        return not_found()
    limit = settings.MAX_PHOTO_MB * 1024 * 1024
    form = await request.form()
    files = []
    for f in form.getlist("photos"):
        if hasattr(f, "read") and getattr(f, "filename", ""):
            files.append(await f.read(limit + 1))  # reading one byte past the limit is enough to reject it
    try:
        store.start_upload(school, files, finder())
    except ValueError as exc:
        log.warning("%s: upload rejected: %s", school, exc)
        return page(pages.staff_page(school, key, error=str(exc)), 400)
    return RedirectResponse(f"/upload/{key}?m=uploaded", status_code=303)


@app.post("/upload/{key}/add")
def add_missed(key: str, description: str = Form("")):
    school = store.school_for_key(key)
    if not school:
        return not_found()
    try:
        store.add_missed(school, description)
    except ValueError as exc:
        return page(pages.staff_page(school, key, error=str(exc)), 400)
    return RedirectResponse(f"/upload/{key}?m=added", status_code=303)


@app.post("/upload/{key}/item/{no}/{action}")
def item_action(key: str, no: int, action: str):
    school = store.school_for_key(key)
    if not school:
        return not_found()
    try:
        store.item_action(school, no, action)
    except (KeyError, ValueError):
        return not_found()
    return RedirectResponse(f"/upload/{key}?m=updated", status_code=303)


def _number(name: str) -> int | None:
    stem, _, ext = name.partition(".")
    return int(stem) if ext == "jpg" and stem.isdigit() else None


@app.get("/upload/{key}/img/{name}")
def staff_image(key: str, name: str):
    school, no = store.school_for_key(key), _number(name)
    if not school or no is None or not store.crop_path(school, no).exists():
        return not_found()
    return FileResponse(store.crop_path(school, no), media_type="image/jpeg")


@app.get("/upload/{key}/overview/{name}")
def staff_overview(key: str, name: str):
    school = store.school_for_key(key)
    path = store.overview_path(school, name) if school else None
    if not path:
        return not_found()
    return FileResponse(path, media_type="image/jpeg")


# ---- public catalog (keep these last: /{school} matches any single word) ------
@app.get("/{school}/img/{name}")
def public_image(school: str, name: str):
    no = _number(name)
    if school not in settings.SCHOOLS or no is None:
        return not_found()
    item = next((i for i in store.load(school)["items"] if i["no"] == no), None)
    if not item or not store.public_photo_ok(item) or not store.crop_path(school, no).exists():
        return not_found()
    return FileResponse(store.crop_path(school, no), media_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=60"})


@app.get("/{school}", response_class=HTMLResponse)
@app.get("/{school}/", response_class=HTMLResponse)
def catalog(school: str):
    if school not in settings.SCHOOLS:
        return not_found()
    return page(pages.catalog_page(school))
