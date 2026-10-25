import io
import json
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import settings  # noqa: E402
import store  # noqa: E402
from app import app  # noqa: E402
from finder import Finder  # noqa: E402

BASE = "https://demo-words.trycloudflare.com"


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    app.state.finder = None
    app.state.public_url = BASE
    return TestClient(app)


def key(school):
    return store.upload_key(school)


def wait_done(school, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        ups = store.load(school)["uploads"].values()
        if ups and all(u["status"] != "processing" for u in ups):
            return list(ups)
        time.sleep(0.1)
    raise AssertionError("still processing")


def upload(client, school, *photos):
    files = [("photos", (f"p{i}.jpg", data, "image/jpeg")) for i, data in enumerate(photos)]
    return client.post(f"/upload/{key(school)}", files=files, follow_redirects=False)


def jpeg(w=1200, h=800, color="gray", exif_rotate=False):
    img = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    if exif_rotate:
        exif = Image.Exif()
        exif[0x0112] = 6
        img.save(buf, format="JPEG", exif=exif)
    else:
        img.save(buf, format="JPEG")
    return buf.getvalue()


def test_public_pages(client):
    r = client.get("/")
    assert r.status_code == 200
    assert all(n in r.text for n in settings.SCHOOLS.values())
    assert "No items right now" in client.get("/cms-west").text
    assert client.get("/cms-west/").status_code == 200
    assert client.get("/not-a-school").status_code == 404
    qr = client.get("/qr").text
    assert qr.count("<svg") == 3 and f"{BASE}/cms-east" in qr
    assert client.get("/").headers["referrer-policy"] == "same-origin"


def test_secret_links(client):
    tokens = store.links()
    assert len(tokens["owner"]) == 32 and all(len(t) == 32 for t in tokens["schools"].values())
    assert client.get("/upload/cms-west-wrongtoken").status_code == 404
    assert client.get(f"/upload/cms-east-{tokens['schools']['cms-west']}").status_code == 404  # other school's token
    r = client.get(f"/upload/{key('cms-west')}")
    assert r.status_code == 200 and "staff page" in r.text
    assert r.headers["referrer-policy"] == "no-referrer" and r.headers["cache-control"] == "no-store"
    assert client.get("/owner/nope").status_code == 404
    owner = client.get(f"/owner/{tokens['owner']}").text
    assert all(f"{BASE}/upload/{s}-{t}" in owner for s, t in tokens["schools"].items())


def test_bad_uploads(client):
    r = upload(client, "cms-west", b"not a photo")
    assert r.status_code == 400 and "couldn" in r.text
    r = upload(client, "cms-west", *[jpeg()] * (settings.MAX_PHOTOS_PER_UPLOAD + 1))
    assert r.status_code == 400 and "at most" in r.text
    r = client.post(f"/upload/{key('cms-west')}", files=[("photos", ("", b"", "application/octet-stream"))],
                    follow_redirects=False)
    assert r.status_code == 400
    # A real photo with no Gemini key: accepted, then reported clearly.
    assert upload(client, "cms-west", jpeg()).status_code == 303
    (up,) = wait_done("cms-west")
    assert up["status"] == "failed" and "No Gemini key" in up["message"]
    assert "No Gemini key" in client.get(f"/upload/{key('cms-west')}").text


def test_upload_limit_per_hour(client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOADS_PER_HOUR", 1)
    assert upload(client, "cms-west", jpeg()).status_code == 303
    wait_done("cms-west")
    r = upload(client, "cms-west", jpeg())
    assert r.status_code == 400 and "uploads this hour" in r.text


def test_staff_buttons(client):
    use_fake_gemini()
    upload(client, "cms-west", jpeg())
    wait_done("cms-west")
    k = key("cms-west")
    shown = [i["no"] for i in store.load("cms-west")["items"] if store.public_photo_ok(i)]
    assert len(shown) >= 3
    one, two, three = shown[:3]

    def act(no, action):
        return client.post(f"/upload/{k}/item/{no}/{action}", follow_redirects=False)

    assert act(one, "picked-up").status_code == 303
    assert f"#{one}</div>" not in client.get("/cms-west").text
    assert act(one, "undo").status_code == 303
    assert f"#{one}</div>" in client.get("/cms-west").text
    assert act(two, "hide-photo").status_code == 303
    assert client.get(f"/cms-west/img/{two}.jpg").status_code == 404
    assert act(two, "show-photo").status_code == 303
    assert client.get(f"/cms-west/img/{two}.jpg").status_code == 200
    assert act(three, "remove").status_code == 303
    assert "Recently picked up or removed" in client.get(f"/upload/{k}").text
    assert act(999, "remove").status_code == 404
    assert act(1, "explode").status_code == 404
    r = client.post(f"/upload/{k}/add", data={"description": "  Pile of about 12 keys  "}, follow_redirects=False)
    assert r.status_code == 303
    items = store.load("cms-west")["items"]
    item = items[-1]
    assert item["no"] == max(i["no"] for i in items[:-1]) + 1 and item["category"] == "keys" and item["en"] == "Pile of about 12 keys"
    assert "Pile of about 12 keys" in client.get("/cms-west").text
    assert client.post(f"/upload/{k}/add", data={"description": "   "}).status_code == 400


def test_owner_new_link_and_reset(client):
    old = key("cms-west")
    owner = store.links()["owner"]
    use_fake_gemini()
    upload(client, "cms-west", jpeg())
    wait_done("cms-west")
    listed = len(store.public_items("cms-west"))
    assert listed > 0
    assert client.post(f"/owner/{owner}/rotate/cms-west", follow_redirects=False).status_code == 303
    assert client.get(f"/upload/{old}").status_code == 404
    assert client.get(f"/upload/{key('cms-west')}").status_code == 200
    client.post(f"/owner/{owner}/reset/cms-west", data={}, follow_redirects=False)
    assert len(store.public_items("cms-west")) == listed  # not confirmed, nothing deleted
    client.post(f"/owner/{owner}/reset/cms-west", data={"confirm": "yes"}, follow_redirects=False)
    assert store.public_items("cms-west") == []
    assert client.post("/owner/wrong/reset/cms-west", data={"confirm": "yes"}).status_code == 404


def test_restart_fails_unfinished_uploads(client):
    store.save("cms-west", {"next_no": 1, "items": [], "uploads": {
        "cut-off": {"ts": time.time(), "photos": [], "status": "processing", "items": [], "overviews": []}}})
    store.fail_unfinished_uploads()
    (up,) = store.load("cms-west")["uploads"].values()
    assert up["status"] == "failed" and "restarted" in up["message"]
    assert "Finding items" not in client.get(f"/upload/{key('cms-west')}").text


def test_dotenv(tmp_path, monkeypatch):
    from app import load_dotenv
    env = tmp_path / ".env"
    env.write_text('# comment\nexport GEMINI_API_KEY="from-file"\nOTHER_VAR=x\n')
    monkeypatch.setenv("GEMINI_API_KEY", "")      # empty doesn't count as set
    monkeypatch.setenv("OTHER_VAR", "from-shell")  # a real value wins over .env
    load_dotenv(env)
    import os
    assert os.environ["GEMINI_API_KEY"] == "from-file" and os.environ["OTHER_VAR"] == "from-shell"


class FakeInteraction:
    def __init__(self, text):
        self.output_text = text


class FakeGemini:
    """Stands in for google-genai: one bottle with a name label, one phone, one hoodie per view."""

    def __init__(self):
        self.calls = 0
        self.interactions = self

    def create(self, **body):
        self.calls += 1
        assert body["input"][1]["type"] == "image" and body["response_format"]["schema"]
        return FakeInteraction(json.dumps({
            "items": [
                {"label": "water bottle", "category": "bottle", "description_en": "Blue bottle", "has_text": True,
                 "box_2d": [300, 400, 700, 600]},
                {"label": "phone", "category": "electronics", "description_en": "Black phone",
                 "box_2d": [100, 100, 200, 250]},
                {"label": "hoodie", "category": "clothing", "description_en": "Grey hoodie", "has_text": True,
                 "box_2d": [720, 100, 950, 300]},
            ],
            "writing_boxes": [[450, 420, 520, 580]],
        }))


def use_fake_gemini() -> Finder:
    finder = Finder(None, settings.MODEL)
    finder.client = FakeGemini()
    app.state.finder = finder
    return finder


def test_gemini_path_with_a_phone_photo(client):
    finder = use_fake_gemini()
    assert upload(client, "cms-north", jpeg(800, 1200, exif_rotate=True)).status_code == 303
    (up,) = wait_done("cms-north")
    assert up["status"] == "done" and "Gemini" in up["message"]
    assert finder.client.calls == 7  # whole photo + 6 tiles
    items = store.load("cms-north")["items"]
    by_cat = {}
    for i in items:
        by_cat.setdefault(i["category"], []).append(i)
    assert all(not store.public_photo_ok(i) for i in by_cat["electronics"])          # valuables: never pictured
    assert all(i["names_blurred"] and i["show_photo"] for i in by_cat["bottle"])      # name blurred, shown
    assert all(not i["show_photo"] for i in by_cat["clothing"])                       # name seen, not placed: hidden
    photo = Image.open(store.folder("cms-north") / "photos" / up["photos"][0])
    assert photo.size == (1200, 800) and not photo.getexif().get(0x0112)               # rotated upright, EXIF gone


def test_log_hides_secret_links():
    from app import safe_path
    assert safe_path("/upload/cms-east-3f9cab12") == "/upload/cms-east-***"
    assert safe_path("/upload/cms-west-3f9cab12/item/4/remove") == "/upload/cms-west-***/item/4/remove"
    assert safe_path("/owner/abc123/reset/cms-west") == "/owner/***/reset/cms-west"
    assert safe_path("/cms-east/img/3.jpg") == "/cms-east/img/3.jpg"


def test_upload_is_logged(client, caplog):
    use_fake_gemini()
    with caplog.at_level("INFO", logger="snapsortai"):
        upload(client, "cms-west", jpeg())
        wait_done("cms-west")
    text = caplog.text
    assert "upload" in text and "accepted" in text and "items listed" in text and "Gemini found" in text
    assert store.links()["schools"]["cms-west"] not in text  # no secret tokens in the log
