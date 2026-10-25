"""Demo settings. Edit these, then run run_demo.py.

Your Gemini key does NOT go here. Put it in a file called .env in this folder
containing one line:  GEMINI_API_KEY=...   (it's read when the app starts).
"""

SCHOOLS = {
    "cms-east": "Coppell Middle School East",
    "cms-north": "Coppell Middle School North",
    "cms-west": "Coppell Middle School West",
}

# Which Gemini model finds the items.
#   "gemini-3.8-flash"            Google's own object-detection examples use this one (default)
#   "gemini-3.5-flash-lite"       cheaper
#   "gemini-3.1-flash-lite-image" Nano Banana 2 Lite (an image-generation model; try it if you like)
MODEL = "gemini-3.5-flash-lite"

GEMINI_TIMEOUT_S = 60         # give up on one Gemini call after this long (then retry, up to 3 tries)

DAYS_LISTED = 30              # items leave the public page after this many days

PORT = 8000
USE_TUNNEL = True             # True: a free public https link through Cloudflare (needs cloudflared)
KEEP_AWAKE = True             # Mac only: stop the laptop sleeping while the demo runs

# How much the app logs, to the terminal and to data/app.log.
#   "INFO"  uploads, Gemini results, staff actions, problems (default)
#   "DEBUG" also every page request
LOG_LEVEL = "INFO"

# Limits, so a forwarded upload link can't flood a school's page.
MAX_PHOTOS_PER_UPLOAD = 6
MAX_PHOTO_MB = 15
MAX_UPLOADS_PER_HOUR = 10     # per school
