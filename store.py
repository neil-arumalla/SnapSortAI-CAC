"""Everything the demo saves lives in data/ on this laptop.

data/links.json            the secret tokens in the upload and owner links
data/<school>/items.json   that school's items and uploads
data/<school>/photos/      uploaded shelf photos (private; rotation fixed, GPS removed)
data/<school>/crops/       one picture per item (names blurred where found)
data/<school>/overviews/   shelf photos with numbered boxes (staff only)
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import re
import secrets
import shutil
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import settings
from finder import VALUABLES, NoKeyError, category_of, crop_with_names_hidden, jpeg_bytes, load_photo, overview

log = logging.getLogger("snapsortai.store")
DATA = Path(os.environ.get("SNAPSORTAI_DATA") or Path(__file__).resolve().parent / "data")
_school_locks = {s: threading.RLock() for s in settings.SCHOOLS}
_links_lock = threading.RLock()
SAFE_NAME = re.compile(r"^[0-9A-Za-z-]+\.jpg$")


def _read(path: Path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Secret links (no logins: the long random part of the link is the key)
# ---------------------------------------------------------------------------
def links() -> dict:
    with _links_lock:
        path = DATA / "links.json"
        data = _read(path, {})
        changed = False
        if not data.get("owner"):
            data["owner"], changed = secrets.token_hex(16), True
        data.setdefault("schools", {})
        for school in settings.SCHOOLS:
            if not data["schools"].get(school):
                data["schools"][school], changed = secrets.token_hex(16), True
        if changed:
            _write(path, data)
        return data


def rotate_link(school: str) -> None:
    """Give a school a new upload link; the old one stops working at once."""
    with _links_lock:
        data = links()
        data["schools"][school] = secrets.token_hex(16)
        _write(DATA / "links.json", data)
    log.info("%s: new upload link made; the old one stopped working", school)


def upload_key(school: str) -> str:
    return f"{school}-{links()['schools'][school]}"


def school_for_key(key: str) -> str | None:
    school, _, token = (key or "").rpartition("-")
    if school not in settings.SCHOOLS or not token:
        return None
    return school if hmac.compare_digest(token, links()["schools"][school]) else None


def is_owner(token: str) -> bool:
    return hmac.compare_digest(token or "", links()["owner"])


# ---------------------------------------------------------------------------
# A school's items
# ---------------------------------------------------------------------------
def folder(school: str) -> Path:
    return DATA / school


def load(school: str) -> dict:
    data = _read(folder(school) / "items.json", {"next_no": 1, "uploads": {}, "items": []})
    data["next_no"] = max([int(data.get("next_no", 1))] + [int(i["no"]) + 1 for i in data["items"]])
    return data


def save(school: str, data: dict) -> None:
    _write(folder(school) / "items.json", data)


def expired(item: dict) -> bool:
    return item.get("found", "") < (date.today() - timedelta(days=settings.DAYS_LISTED)).isoformat()


def public_items(school: str) -> list[dict]:
    return sorted((i for i in load(school)["items"] if i["status"] == "listed" and not expired(i)),
                  key=lambda i: -i["no"])


def public_photo_ok(item: dict) -> bool:
    return (item["status"] == "listed" and not expired(item) and item.get("show_photo")
            and item.get("has_crop") and item["category"] not in VALUABLES)


def crop_path(school: str, no: int) -> Path:
    return folder(school) / "crops" / f"{int(no)}.jpg"


def overview_path(school: str, name: str) -> Path | None:
    if not SAFE_NAME.match(name or ""):
        return None
    path = folder(school) / "overviews" / name
    return path if path.exists() else None


# ---------------------------------------------------------------------------
# Uploads: save the photos, then find items in the background
# ---------------------------------------------------------------------------
def uploads_last_hour(data: dict) -> int:
    cutoff = time.time() - 3600
    return sum(1 for u in data["uploads"].values() if u.get("ts", 0) >= cutoff)


def start_upload(school: str, photos: list[bytes], finder) -> str:
    if not photos:
        raise ValueError("Choose at least one photo.")
    if len(photos) > settings.MAX_PHOTOS_PER_UPLOAD:
        raise ValueError(f"Please upload at most {settings.MAX_PHOTOS_PER_UPLOAD} photos at a time.")
    images = []
    for n, raw in enumerate(photos, 1):
        if len(raw) > settings.MAX_PHOTO_MB * 1024 * 1024:
            raise ValueError(f"Photo {n} is bigger than {settings.MAX_PHOTO_MB} MB.")
        try:
            images.append(load_photo(raw))
        except Exception:
            raise ValueError(f"Photo {n} couldn't be opened. On an iPhone, set Settings > Camera > "
                             "Formats > Most Compatible, then take the photo again.") from None
    with _school_locks[school]:
        data = load(school)
        if uploads_last_hour(data) >= settings.MAX_UPLOADS_PER_HOUR:
            raise ValueError("That's a lot of uploads this hour. Please try again later.")
        upload_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
        names = []
        for n, img in enumerate(images, 1):
            name = f"{upload_id}-{n}.jpg"
            (folder(school) / "photos").mkdir(parents=True, exist_ok=True)
            (folder(school) / "photos" / name).write_bytes(jpeg_bytes(img, quality=90))
            names.append(name)
        data["uploads"][upload_id] = {"ts": time.time(), "at": datetime.now().isoformat(timespec="minutes"),
                                      "photos": names, "status": "processing", "items": [],
                                      "overviews": [], "message": "", "by": "staff"}
        save(school, data)
    log.info("%s: upload %s accepted, %d photo(s), %.1f MB", school, upload_id, len(photos),
             sum(map(len, photos)) / 1e6)
    threading.Thread(target=_process, args=(school, upload_id, finder), daemon=True).start()
    return upload_id


def _process(school: str, upload_id: str, finder) -> None:
    started = time.monotonic()
    photos = load(school)["uploads"][upload_id]["photos"]
    notes, problems = set(), []
    for n, name in enumerate(photos, 1):
        try:
            img = load_photo((folder(school) / "photos" / name).read_bytes())
            items, writing, how = finder.find(img)
            add_found_items(school, upload_id, name, img, items, writing)
            notes.add(how)
            log.info("%s: upload %s photo %d/%d: %d items listed", school, upload_id, n, len(photos), len(items))
        except NoKeyError as exc:
            log.error("%s: upload %s photo %d/%d: %s", school, upload_id, n, len(photos), exc)
            problems.append(str(exc))
        except Exception as exc:  # keep going with the other photos
            log.exception("%s: upload %s photo %d/%d couldn't be processed", school, upload_id, n, len(photos))
            problems.append(f"A photo couldn't be processed ({type(exc).__name__}). Please try again.")
    status = "failed" if len(problems) == len(photos) else "done"
    (log.error if status == "failed" else log.warning if problems else log.info)(
        "%s: upload %s %s in %.0fs (%d of %d photos had problems)", school, upload_id, status,
        time.monotonic() - started, len(problems), len(photos))
    _finish(school, upload_id, status, " ".join(sorted(set(problems))) or "; ".join(sorted(notes)))


def fail_unfinished_uploads() -> None:
    """Uploads still "processing" at startup were cut off by a restart; their work is lost."""
    for school in settings.SCHOOLS:
        with _school_locks[school]:
            data = load(school)
            stuck = [u for u in data["uploads"].values() if u["status"] == "processing"]
            for u in stuck:
                log.warning("%s: an upload from %s was cut off by a restart; marked failed", school, u.get("at", "?"))
                u.update(status="failed", message="The app restarted before this upload finished. Please upload again.")
            if stuck:
                save(school, data)


def _finish(school: str, upload_id: str, status: str, message: str) -> None:
    with _school_locks[school]:
        data = load(school)
        if upload_id in data["uploads"]:
            data["uploads"][upload_id].update(status=status, message=message)
            save(school, data)


def add_found_items(school: str, upload_id: str, photo_name: str, img, items: list[dict], writing: list) -> None:
    with _school_locks[school]:
        data = load(school)
        today = date.today().isoformat()
        numbered = []
        (folder(school) / "crops").mkdir(parents=True, exist_ok=True)
        (folder(school) / "overviews").mkdir(parents=True, exist_ok=True)
        for it in items:
            no = data["next_no"]
            data["next_no"] += 1
            crop, blurred, unplaced_name = crop_with_names_hidden(img, it, writing)
            crop.save(crop_path(school, no), quality=85)
            data["items"].append({
                "no": no, "status": "listed", "found": today, "category": it["category"],
                "en": str(it.get("description_en") or it.get("label") or "Item")[:160],
                "es": str(it.get("description_es") or "")[:160],
                "pile": bool(it.get("is_pile")), "count": int(it.get("count") or 1),
                "show_photo": not unplaced_name, "why_hidden": "name label" if unplaced_name else "",
                "names_blurred": blurred, "has_crop": True,
                "upload": upload_id, "photo": photo_name, "box": list(it["box"]),
            })
            numbered.append((no, it["box"]))
        name = Path(photo_name).stem + ".jpg"
        overview(img, numbered).save(folder(school) / "overviews" / name, quality=82)
        upload = data["uploads"].get(upload_id)
        if upload is not None:
            upload["items"] += [n for n, _ in numbered]
            upload["overviews"].append(name)
        save(school, data)


# ---------------------------------------------------------------------------
# Staff buttons
# ---------------------------------------------------------------------------
ACTIONS = {
    "picked-up": ("status", "picked_up"),
    "remove": ("status", "removed"),
    "undo": ("status", "listed"),
    "hide-photo": ("show_photo", False),
    "show-photo": ("show_photo", True),
}


def item_action(school: str, no: int, action: str) -> None:
    if action not in ACTIONS:
        raise ValueError("Unknown action")
    with _school_locks[school]:
        data = load(school)
        item = next((i for i in data["items"] if i["no"] == no), None)
        if item is None:
            raise KeyError(no)
        field, value = ACTIONS[action]
        item[field] = value
        if field == "status":
            item["status_at"] = datetime.now().isoformat(timespec="minutes")
        else:
            item["why_hidden"] = "" if value else "hidden by staff"
        save(school, data)
    log.info("%s: item #%d %s", school, no, action)


def add_missed(school: str, text: str) -> int:
    text = " ".join((text or "").split())[:160]
    if not text:
        raise ValueError("Describe the item first.")
    with _school_locks[school]:
        data = load(school)
        no = data["next_no"]
        data["items"].append({
            "no": no, "status": "listed", "found": date.today().isoformat(),
            "category": category_of({"label": text}), "en": text, "es": "", "pile": False, "count": 1,
            "show_photo": False, "why_hidden": "added by hand", "names_blurred": False, "has_crop": False,
            "upload": "", "photo": "", "box": [],
        })
        save(school, data)
    log.info("%s: item #%d added by hand", school, no)
    return no


def reset_school(school: str) -> None:
    """Delete everything for a school (for repeat demos)."""
    with _school_locks[school]:
        shutil.rmtree(folder(school), ignore_errors=True)
    log.warning("%s: reset, all items and photos deleted", school)
