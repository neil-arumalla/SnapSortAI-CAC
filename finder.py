"""Find lost items in a shelf photo with Gemini, then crop them and blur names.

The photo is checked as a whole and in 6 overlapping pieces (more items are found
that way), the results are merged, and each item gets a crop. Any writing Gemini
marks as a possible name is pixelated.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import math
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("snapsortai.gemini")
Image.MAX_IMAGE_PIXELS = 80_000_000  # refuse absurdly large images

try:  # lets iPhone HEIC photos open, if the optional pillow-heif package is installed
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

CATEGORIES = {  # id: (English, Spanish)
    "bottle": ("Water bottles", "Botellas de agua"),
    "lunchbox": ("Lunch boxes", "Loncheras"),
    "bag": ("Bags & backpacks", "Mochilas y bolsas"),
    "clothing": ("Clothing", "Ropa"),
    "hat": ("Hats", "Gorras y gorros"),
    "gloves_scarf": ("Gloves & scarves", "Guantes y bufandas"),
    "shoes": ("Shoes", "Zapatos"),
    "eyewear": ("Glasses & sunglasses", "Lentes"),
    "keys": ("Keys", "Llaves"),
    "jewelry_watch": ("Jewelry & watches", "Joyas y relojes"),
    "electronics": ("Electronics", "Electrónicos"),
    "wallet_id": ("Wallets & IDs", "Carteras e identificaciones"),
    "school_supplies": ("School supplies", "Útiles escolares"),
    "sports": ("Sports gear", "Equipo deportivo"),
    "other": ("Other", "Otros"),
}
VALUABLES = {"keys", "jewelry_watch", "electronics", "wallet_id"}  # never pictured on the public page
LABEL_TO_CATEGORY = {
    "water bottle": "bottle", "bottle": "bottle", "tumbler": "bottle", "thermos": "bottle",
    "lunch box": "lunchbox", "lunch bag": "lunchbox", "backpack": "bag", "messenger bag": "bag",
    "bag": "bag", "hoodie": "clothing", "jacket": "clothing", "sweater": "clothing",
    "sweatshirt": "clothing", "shirt": "clothing", "coat": "clothing", "beanie": "hat", "cap": "hat",
    "hat": "hat", "glove": "gloves_scarf", "scarf": "gloves_scarf", "shoe": "shoes", "sneaker": "shoes",
    "sunglasses": "eyewear", "glasses": "eyewear", "key": "keys", "watch": "jewelry_watch",
    "bracelet": "jewelry_watch", "necklace": "jewelry_watch", "earring": "jewelry_watch",
    "phone": "electronics", "tablet": "electronics", "earbuds": "electronics", "headphones": "electronics",
    "charger": "electronics", "calculator": "electronics", "wallet": "wallet_id", "book": "school_supplies",
    "notebook": "school_supplies", "binder": "school_supplies", "ball": "sports",
}

PROMPT = f"""You are cataloguing a photo of a school lost-and-found area so that students and parents can recognise their belongings.

Find EVERY separate lost item: water bottles, lunch boxes, backpacks, bags, jackets, hoodies, sweaters, hats, gloves, scarves, shoes, sunglasses, glasses, keys, jewelry, watches, phones, tablets, earbuds, chargers, books, sports gear and anything else a student could lose.

Rules:
1. One entry per physical item. Stacked or folded items are separate entries when you can see each one.
2. Small items heaped together that cannot be separated (a pile of keys, a tangle of chargers): ONE entry with "is_pile": true and an estimated "count".
3. Ignore shelves, walls, signs, bins, furniture and people.
4. Fit each box_2d tightly around the item: [ymin, xmin, ymax, xmax] normalized to 0-1000.
5. NEVER copy personal names or other writing into your answer. If an item shows a name label, handwriting or a printed name, set "has_text": true AND add a box_2d around that writing to "writing_boxes".
6. Descriptions help a parent recognise the item: colour, type, distinctive details (stickers, patterns, cap or zipper style), at most 12 words, in English and Spanish. Mention a brand only if its logo is clearly readable.
7. "category" must be one of: {", ".join(CATEGORIES)}.
"""

BOX = {"type": "array", "items": {"type": "integer"}}
SCHEMA = {
    "type": "object",
    "properties": {
        "items": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "label": {"type": "string"},
                "category": {"type": "string", "enum": list(CATEGORIES)},
                "description_en": {"type": "string"},
                "description_es": {"type": "string"},
                "has_text": {"type": "boolean"},
                "is_pile": {"type": "boolean"},
                "count": {"type": "integer"},
                "box_2d": {**BOX, "description": "[ymin, xmin, ymax, xmax] normalized to 0-1000"},
            },
            "required": ["label", "category", "description_en", "box_2d"],
        }},
        "writing_boxes": {"type": "array", "items": BOX,
                          "description": "box_2d around every name label or piece of writing on an item"},
    },
    "required": ["items"],
}


class NoKeyError(RuntimeError):
    """Raised when a new photo needs Gemini but no key is set."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def load_photo(data: bytes) -> Image.Image:
    """Open a photo, apply the phone's rotation and drop all metadata (including GPS)."""
    with Image.open(io.BytesIO(data)) as raw:
        img = ImageOps.exif_transpose(raw).convert("RGB")
    if max(img.size) > 4096:
        img.thumbnail((4096, 4096), Image.LANCZOS)
    return img


def jpeg_bytes(img: Image.Image, quality: int = 88, max_edge: int | None = None) -> bytes:
    if max_edge and max(img.size) > max_edge:
        img = img.copy()
        img.thumbnail((max_edge, max_edge), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _box(value) -> list[float] | None:
    """Validate [ymin, xmin, ymax, xmax] on 0-1000 and return it as x0, y0, x1, y1."""
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        ymin, xmin, ymax, xmax = (min(1000.0, max(0.0, float(v))) for v in value)
    except (TypeError, ValueError):
        return None
    x0, x1 = sorted((xmin, xmax))
    y0, y1 = sorted((ymin, ymax))
    return [x0, y0, x1, y1] if x1 - x0 >= 1 and y1 - y0 >= 1 else None


def parse_reply(text: str) -> dict:
    """Read the model's JSON, tolerating code fences; drop anything malformed."""
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text[text.find("{"):] if "{" in text else text)
    except json.JSONDecodeError:
        return {"items": [], "writing_boxes": []}
    if isinstance(data, list):
        data = {"items": data}
    items = [i for i in data.get("items", []) if isinstance(i, dict) and _box(i.get("box_2d"))]
    writing = [b for b in data.get("writing_boxes", []) if _box(b)]
    return {"items": items, "writing_boxes": writing}


def tiles(w: int, h: int, max_tile: int = 1600, overlap_frac: float = 0.2) -> list[tuple]:
    cols, rows = max(2, math.ceil(w / max_tile)), max(2, math.ceil(h / max_tile))
    if w / h >= 1.5:
        cols = max(cols, 3)
    if h / w >= 1.5:
        rows = max(rows, 3)
    tw = min(w, math.ceil(w / cols * (1 + overlap_frac)))
    th = min(h, math.ceil(h / rows * (1 + overlap_frac)))
    xs = [round(i * (w - tw) / (cols - 1)) for i in range(cols)]
    ys = [round(j * (h - th) / (rows - 1)) for j in range(rows)]
    return [(x, y, x + tw, y + th) for y in ys for x in xs]


def to_pixels(box1000, region) -> tuple[int, int, int, int]:
    rx0, ry0, rx1, ry1 = region
    x0, y0, x1, y1 = box1000
    return (int(rx0 + x0 / 1000 * (rx1 - rx0)), int(ry0 + y0 / 1000 * (ry1 - ry0)),
            int(rx0 + x1 / 1000 * (rx1 - rx0)), int(ry0 + y1 / 1000 * (ry1 - ry0)))


def area(b) -> int:
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def overlap(a, b) -> int:
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def iou(a, b) -> float:
    inter = overlap(a, b)
    return inter / (area(a) + area(b) - inter or 1)


def cut_by_tile_edge(box, tile, w, h) -> bool:
    """A box touching an inner tile edge is a partial item; the neighbour tile sees it whole."""
    mx, my = max(2, int((tile[2] - tile[0]) * 0.015)), max(2, int((tile[3] - tile[1]) * 0.015))
    return ((tile[0] > 0 and box[0] <= tile[0] + mx) or (tile[1] > 0 and box[1] <= tile[1] + my)
            or (tile[2] < w and box[2] >= tile[2] - mx) or (tile[3] < h and box[3] >= tile[3] - my))


def category_of(item: dict) -> str:
    cat = str(item.get("category") or "").strip().lower()
    if cat in CATEGORIES:
        return cat
    label = str(item.get("label") or "").lower()
    for word, mapped in sorted(LABEL_TO_CATEGORY.items(), key=lambda kv: -len(kv[0])):
        if word in label:
            return mapped
    return "other"


def merge(found: list[dict], w: int, h: int) -> list[dict]:
    """Drop whole-shelf and tiny boxes, group boxes, and near-identical duplicates."""
    cand = [d for d in found if area(d["box"]) <= 0.4 * w * h
            and d["box"][2] - d["box"][0] >= 8 and d["box"][3] - d["box"][1] >= 8]
    groups = {i for i, a in enumerate(cand)
              if sum(1 for j, b in enumerate(cand) if i != j and a["category"] == b["category"]
                     and area(b["box"]) < area(a["box"]) and overlap(a["box"], b["box"]) >= 0.85 * area(b["box"])) >= 2}
    cand = [d for i, d in enumerate(cand) if i not in groups]
    kept = []
    for d in sorted(cand, key=lambda d: (d["source"] == "full", -area(d["box"]))):  # tiles see more detail
        if not any(k["category"] == d["category"] and iou(k["box"], d["box"]) >= 0.7 for k in kept):
            kept.append(d)
    band = max(1, int(h * 0.08))  # numbering order: shelf by shelf, left to right
    return sorted(kept, key=lambda d: (((d["box"][1] + d["box"][3]) // 2) // band, (d["box"][0] + d["box"][2]) // 2))


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------
class Finder:
    def __init__(self, api_key: str | None, model: str, timeout_s: int = 60):
        self.model = model
        self.client = None
        if api_key:
            from google import genai  # only needed when a key is set
            from google.genai import types
            self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=timeout_s * 1000))

    @property
    def has_key(self) -> bool:
        return self.client is not None

    def ask(self, view: Image.Image, name: str = "full") -> dict:
        """One Gemini call; returns 0-1000 boxes relative to `view`."""
        for attempt in range(3):
            started = time.monotonic()
            try:
                interaction = self.client.interactions.create(
                    model=self.model,
                    input=[
                        {"type": "text", "text": PROMPT},
                        {"type": "image", "data": base64.b64encode(jpeg_bytes(view, max_edge=1600)).decode(),
                         "mime_type": "image/jpeg"},
                    ],
                    response_format={"type": "text", "mime_type": "application/json", "schema": SCHEMA},
                    generation_config={"thinking_level": "minimal"},
                )
                text = getattr(interaction, "output_text", "") or ""
                reply = parse_reply(text)
                log.info("%s: %d items, %d writing boxes in %.1fs", name, len(reply["items"]),
                          len(reply["writing_boxes"]), time.monotonic() - started)
                if text.strip() and not reply["items"] and "{" not in text:
                    log.warning("%s: Gemini's reply wasn't JSON, so nothing was read from it", name)
                return reply
            except Exception as exc:  # network hiccup or rate limit: wait and retry
                if attempt == 2:
                    log.error("%s: Gemini call failed 3 times, giving up: %s", name, _describe(exc))
                    raise
                wait = 4 * (attempt + 1)
                log.warning("%s: Gemini call failed (try %d of 3), retrying in %ds: %s",
                            name, attempt + 1, wait, _describe(exc))
                time.sleep(wait)
        return {"items": [], "writing_boxes": []}

    def find(self, img: Image.Image) -> tuple[list[dict], list[tuple], str]:
        """Returns (items, writing boxes, how they were found)."""
        if not self.has_key:
            raise NoKeyError("No Gemini key is set. Add GEMINI_API_KEY to the .env file and restart.")
        w, h = img.size
        regions = [("full", (0, 0, w, h))] + [(f"tile{i}", t) for i, t in enumerate(tiles(w, h))]

        def run(job):
            name, region = job
            return name, region, self.ask(img if name == "full" else img.crop(region), name)

        started = time.monotonic()
        log.info("Asking %s about a %dx%d photo (%d calls)", self.model, w, h, len(regions))
        found, writing = [], []
        with ThreadPoolExecutor(max_workers=4) as pool:
            for name, region, reply in pool.map(run, regions):
                for item in reply["items"]:
                    box = to_pixels(_box(item["box_2d"]), region)
                    if name != "full" and cut_by_tile_edge(box, region, w, h):
                        continue
                    found.append({**item, "box": box, "category": category_of(item), "source": name})
                writing += [to_pixels(_box(b), region) for b in reply["writing_boxes"]]
        items = merge(found, w, h)
        log.info("Gemini found %d boxes, %d items after merging duplicates, %d name labels, in %.1fs",
                 len(found), len(items), len(writing), time.monotonic() - started)
        return items, writing, f"Gemini ({self.model}), {len(regions)} calls"


def _describe(exc: Exception) -> str:
    """Short error text for the log, with the API key blanked out in case an error repeats it."""
    text = f"{type(exc).__name__}: {exc}"[:300]
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return text.replace(key, "<key>") if key else text


# ---------------------------------------------------------------------------
# Crops and the numbered overview picture
# ---------------------------------------------------------------------------
def pixelate(img: Image.Image, boxes) -> Image.Image:
    out = img.copy()
    for x0, y0, x1, y1 in boxes:
        ex, ey = int((x1 - x0) * 0.15) + 2, int((y1 - y0) * 0.15) + 2
        r = (max(0, x0 - ex), max(0, y0 - ey), min(out.width, x1 + ex), min(out.height, y1 + ey))
        rw, rh = r[2] - r[0], r[3] - r[1]
        if rw > 2 and rh > 2:
            block = max(4, min(rw, rh) // 6)
            small = out.crop(r).resize((max(1, rw // block), max(1, rh // block)), Image.BILINEAR)
            out.paste(small.resize((rw, rh), Image.NEAREST), r[:2])
    return out


def crop_item(img: Image.Image, box) -> Image.Image:
    x0, y0, x1, y1 = box
    dx, dy = max(6, int((x1 - x0) * 0.04)), max(6, int((y1 - y0) * 0.04))
    crop = img.crop((max(0, x0 - dx), max(0, y0 - dy), min(img.width, x1 + dx), min(img.height, y1 + dy)))
    crop.thumbnail((900, 900), Image.LANCZOS)
    return crop


def crop_with_names_hidden(img: Image.Image, item: dict, writing: list[tuple]) -> tuple[Image.Image, bool, bool]:
    """Returns (crop, a name was blurred, the AI saw a name on this item but couldn't place it)."""
    around = (item["box"][0] - 30, item["box"][1] - 30, item["box"][2] + 30, item["box"][3] + 30)
    names = [b for b in writing if overlap(b, around)]
    own = [b for b in names if overlap(b, item["box"]) >= 0.5 * max(1, area(b))]
    crop = crop_item(pixelate(img, names) if names else img, item["box"])
    return crop, bool(names), bool(item.get("has_text")) and not own


def overview(img: Image.Image, numbered: list[tuple[int, list]]) -> Image.Image:
    """The shelf photo with a numbered box on every item found."""
    out = img.copy()
    out.thumbnail((1600, 1600), Image.LANCZOS)
    s = out.width / img.width
    draw = ImageDraw.Draw(out)
    try:
        font = ImageFont.load_default(size=max(12, out.width // 70))
    except TypeError:
        font = ImageFont.load_default()
    for no, box in numbered:
        x0, y0, x1, y1 = (int(v * s) for v in box)
        draw.rectangle([x0, y0, x1, y1], outline=(0, 220, 120), width=max(2, out.width // 500))
        draw.rectangle([x0, y0, x0 + 10 + 9 * len(str(no)), y0 + 20], fill=(0, 0, 0))
        draw.text((x0 + 4, y0 + 2), str(no), fill=(0, 220, 120), font=font)
    return out
