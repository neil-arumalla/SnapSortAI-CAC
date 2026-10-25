#!/usr/bin/env python3
"""Start SnapSortAI. Hit Run in IntelliJ (or: python run_demo.py).

1. Starts the website on this laptop.
2. Opens a free public https link through Cloudflare (if cloudflared is installed).
3. Prints every link and opens your owner page.
Press Ctrl+C, or IntelliJ's Stop button, to take it all offline.
"""
from __future__ import annotations

import atexit
import logging
import logging.handlers
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

TUNNEL_URL = re.compile(r"https://[-a-z0-9]+\.trycloudflare\.com")
_children: list[subprocess.Popen] = []
log = logging.getLogger("snapsortai")


def setup_logging(level: str, log_path: Path) -> None:
    """Log to the terminal and to data/app.log (kept to 5 x 1 MB)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S")
    file = logging.handlers.RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5)
    file.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root = logging.getLogger("snapsortai")
    root.setLevel(level.upper())
    root.addHandler(file)
    root.addHandler(console)
    logging.getLogger("uvicorn.error").addHandler(file)  # server crashes go to the file too


def stop_children() -> None:
    for proc in _children:
        if proc.poll() is None:
            proc.terminate()


def _stop_on_sigterm(*_args) -> None:
    raise KeyboardInterrupt  # IntelliJ's Stop button and `kill` end the demo the same way as Ctrl+C


def keep_awake(enabled: bool) -> None:
    if enabled and sys.platform == "darwin" and shutil.which("caffeinate"):
        _children.append(subprocess.Popen(["caffeinate", "-is", "-w", str(os.getpid())]))


def start_server(app, port: int):
    import uvicorn

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(150):
        try:
            opener.open(f"http://127.0.0.1:{port}/healthz", timeout=1)
            return server
        except Exception:
            time.sleep(0.2)
    sys.exit(f"The website didn't start. Is another program using port {port}? Change PORT in settings.py.")


def start_tunnel(port: int, log_path: Path) -> str | None:
    exe = shutil.which("cloudflared")
    if not exe:
        print("\n  cloudflared isn't installed, so the demo only works on this laptop.\n"
              "  To get a public link: brew install cloudflared   then run this again.\n")
        return None
    proc = subprocess.Popen([exe, "tunnel", "--url", f"http://127.0.0.1:{port}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    _children.append(proc)
    found: dict[str, str] = {}
    ready = threading.Event()

    def pump():  # keep reading cloudflared's output so it never blocks
        with open(log_path, "a") as log:
            for line in proc.stdout:
                log.write(line)
                log.flush()
                match = TUNNEL_URL.search(line)
                if match and "url" not in found:
                    found["url"] = match.group(0)
                    ready.set()
        ready.set()

    threading.Thread(target=pump, daemon=True).start()
    log.info("Asking Cloudflare for a public link")
    ready.wait(60)
    if "url" not in found:
        log.warning("Couldn't get a public link (details in %s). The demo works on this laptop only.", log_path)
        proc.terminate()
        return None
    time.sleep(3)  # give the new address a moment to start answering
    log.info("Public link is up")
    return found["url"]


def print_links(base: str, local: str, settings, store) -> None:
    tokens = store.links()
    width = max(len(n) for n in settings.SCHOOLS.values())
    line = "=" * 78
    print(f"\n{line}\n  SNAPSORTAI IS RUNNING\n{line}")
    print("\n  Public pages (share with families):")
    for s, n in settings.SCHOOLS.items():
        print(f"    {n:<{width}}  {base}/{s}")
    print(f"    QR codes to show on screen:  {base}/qr")
    print("\n  Staff upload links (send each school ONLY its own):")
    for s, n in settings.SCHOOLS.items():
        print(f"    {n:<{width}}  {base}/upload/{s}-{tokens['schools'][s]}")
    print("\n  Your owner page (keep it to yourself):")
    print(f"    {local}/owner/{tokens['owner']}")
    if base != local:
        print(f"    from your phone: {base}/owner/{tokens['owner']}")
    print("\n  Gemini key: set (from .env or the environment)")
    print(f"  Model: {settings.MODEL}")
    print("\n  Stop with Ctrl+C or IntelliJ's Stop button. The links change every time you restart.")
    print(f"{line}\n")


def main() -> None:
    import settings
    import store
    setup_logging(settings.LOG_LEVEL, store.DATA / "app.log")
    log.info("Starting the demo")
    from app import app  # also reads .env

    if not os.environ.get("GEMINI_API_KEY", "").strip():
        log.error("No GEMINI_API_KEY in .env or the environment; not starting")
        sys.exit("No Gemini key found. Create a file named .env next to run_demo.py with one line:\n"
                 "    GEMINI_API_KEY=<your key>\nthen run this again.")
    atexit.register(stop_children)
    signal.signal(signal.SIGTERM, _stop_on_sigterm)

    store.links()
    store.fail_unfinished_uploads()
    keep_awake(settings.KEEP_AWAKE)
    server = start_server(app, settings.PORT)
    local = f"http://localhost:{settings.PORT}"
    public = start_tunnel(settings.PORT, store.DATA / "cloudflared.log") if settings.USE_TUNNEL else None
    base = public or local
    app.state.public_url = base
    print_links(base, local, settings, store)
    if not os.environ.get("SNAPSORTAI_NO_BROWSER"):
        webbrowser.open(f"{local}/owner/{store.links()['owner']}")

    try:
        while True:
            time.sleep(1)
            tunnel = next((p for p in _children if p.args and "tunnel" in p.args), None)
            if tunnel is not None and tunnel.poll() is not None:
                log.error("The Cloudflare link stopped (details in %s). Restart run_demo.py to get a new one.",
                          store.DATA / "cloudflared.log")
                _children.remove(tunnel)
    except KeyboardInterrupt:
        pass
    finally:
        log.info("Stopping. The demo is offline.")
        stop_children()
        server.should_exit = True


if __name__ == "__main__":
    main()
