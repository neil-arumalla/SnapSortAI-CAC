# SnapSortAI: runs on your laptop, works from any phone

The whole app runs on your laptop. A free Cloudflare link puts it on the internet while it runs.
There are no logins: the links themselves decide who can do what.

| Link | Who gets it | What it's for |
|---|---|---|
| Public page, e.g. `…/cms-west` | Families and students | See what's in lost & found |
| Staff link, e.g. `…/upload/cms-west-3f9c…` | Only that school's front office | Upload photos and manage items |
| Owner page, `…/owner/…` | Only you | All three schools; new links; reset for a new demo |
| QR page, `…/qr` | Anyone (show it on screen) | QR codes for the three public pages |

---

## 1. Set up (once)

1. **Use a personal laptop.** Company laptops often don't allow public tunnels.
2. **Install the Python packages.** Open a terminal in this folder (or IntelliJ's Terminal tab):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   In IntelliJ, also set the project's Python interpreter to `.venv`.
3. **Install Cloudflare's free tunnel program** (no account needed):
   ```bash
   brew install cloudflared
   ```
   Without it the demo still runs, but only on this laptop (`http://localhost:8000`).
4. **Add your Gemini key.** Never put it in the code, and never share it. Create a file named `.env`
   in this folder containing one line: `GEMINI_API_KEY=<your key>`. It's read when the app starts
   (a non-empty `GEMINI_API_KEY` already set in the environment takes priority). The demo won't start without a key.

## 2. Start it (each demo day)

1. Plug the laptop in. The app keeps the Mac awake while it runs.
2. Right-click **`run_demo.py`** in IntelliJ and choose **Run**, or run `python run_demo.py`.
3. After about 15 seconds the console prints every link, and your owner page opens in the browser:
   ```
   Public pages (share with families):
     Coppell Middle School East   https://<random-words>.trycloudflare.com/cms-east
     ...
   Staff upload links (send each school ONLY its own):
     Coppell Middle School West   https://<random-words>.trycloudflare.com/upload/cms-west-3f9c...
   ```
4. Text or email each front office **its own** staff link, and only theirs.
5. Share the public links, or open the **QR page** (`…/qr`) on screen so people can scan it.
   **Don't print posters yet:** the address changes every time you restart.
6. To finish, press **Stop** in IntelliJ (or Ctrl+C). The site goes offline right away.

All three schools start empty. Upload a photo from each school's staff link to fill its page.
If the app is stopped while an upload is still being processed, that upload shows as failed on the next start; upload it again.

---

## 3. School front office (staff link)

**First time**
1. Open the staff link on a phone or computer.
2. Bookmark it, or add it to the home screen. Don't forward or post it: anyone who has it can upload for the school.

**Uploading photos**
1. Tap **Choose files**. On a phone this offers *Take Photo* or *Photo Library*. You can add up to 6 photos.
2. For good photos:
   - Photograph one shelf or table per photo, in good light.
   - Spread out piles so each item shows.
   - Keep students and faces out of the picture.
3. Tap **Upload**. The page says **"Finding items…"** and refreshes by itself. It takes about a minute per photo.
4. Your photo comes back with a **numbered box on every item found**. Anything without a box was missed.
5. The items are already on the public page. There's no approval step.

**Buttons next to each item**
- **Picked up**: the owner collected it, so it leaves the public page.
- **Hide picture**: use this if a child's name is readable. The item stays listed as text only; **Show picture** undoes it.
- **Remove**: use this for something that isn't a lost item, or an item listed twice.
- **Add an item the AI missed** (box above the list): type e.g. "Pile of about 12 keys". It's listed without a picture.
- **Undo**, in *Recently picked up or removed*, fixes a mistake.

**When a family comes to claim something**
1. They give the item number, e.g. "#12".
2. Open the staff link and find #12's picture. Your page shows pictures of every item, including valuables.
3. For valuables (phones, keys, jewelry, wallets) the public page shows no picture. Ask the family to describe
   the item first (colour, case, keychain), then compare it with your picture.
4. Hand it over and tap **Picked up**.

**Every week**
- Photograph the shelves once a week, e.g. every Friday.
- After 30 days an item leaves the public page on its own and appears under **"ready to donate"**.
  Tap **Donated** once it's gone.

---

## 4. Families and students (public link)

1. Open the school's link or scan its QR code.
2. The page is in English and Spanish. Browse by category: water bottles, bags & backpacks, clothing…
3. Find the item and note its number, e.g. **#12**.
4. Go to the front office and say "I'm here for item #12."
5. Items shown as **"Ask at the front office"** are valuables, or items whose picture was hidden. Describe yours to the staff.
6. Don't see it? Ask anyway: the AI sometimes misses things.
7. Unclaimed items are donated after 30 days.

---

## 5. A five-minute live demo

**Before you start:** upload a photo to CMS East so it has items to show. Then open the owner page, find CMS West,
tick the box and click **Reset for a new demo** so CMS West is empty.

1. Open the CMS East public page (`…/cms-east`). Its items are already listed, with categories and numbers.
2. On a phone, open the **CMS West staff link**. Take a photo of a table of real items.
3. Tap **Upload**. While it says "Finding items…", explain the privacy rules:
   names are blurred, valuables never show a picture, and only cropped items are public, never the whole photo.
4. Show the numbered photo on the staff page ("anything without a box was missed"),
   then refresh the CMS West public page: the new numbered items are there.
5. Act out a claim: "I'm here for item #3." Find it on the staff page, tap **Picked up**,
   refresh the public page, and it's gone.

---

## 6. Settings (`settings.py`)

| Setting | Default | Meaning |
|---|---|---|
| `SCHOOLS` | three Coppell middle schools | Link name → school name |
| `MODEL` | `gemini-3.8-flash` | `gemini-3.5-flash-lite` is cheaper; `gemini-3.1-flash-lite-image` is Nano Banana 2 Lite |
| `DAYS_LISTED` | 30 | Days an item stays on the public page |
| `USE_TUNNEL` | `True` | `False` = only on this laptop |
| `MAX_PHOTOS_PER_UPLOAD`, `MAX_PHOTO_MB`, `MAX_UPLOADS_PER_HOUR` | 6, 15, 10 | Limits so a forwarded link can't flood a page |

## 7. Safety, in short

- Staff and owner links are long random codes that can't be guessed. If a link gets passed around, click
  **Make a new upload link** on the owner page; the old link stops working.
- Only crops of items are public, never the whole photo. Gemini is asked to mark names so they can be blurred.
  If it sees a name it can't place, the item gets no public picture. Valuables never get one.
- Photos are rotated upright and their location data (GPS) is removed when they're saved.
- Everything is stored only in `data/` on this laptop. Delete that folder to wipe the demo.
- Ask the school before using real lost-and-found photos. Gemini's terms say users must be 18+, so an adult should own the key.

## 8. If something goes wrong

| Problem | Fix |
|---|---|
| "cloudflared isn't installed" | `brew install cloudflared`, then start again |
| Public link doesn't open right away | Wait 30 seconds and refresh; new Cloudflare links take a moment |
| "No Gemini key found" when starting | Add `GEMINI_API_KEY` to `.env` (step 1.4) and start again |
| "Photo couldn't be opened" (iPhone) | iPhone Settings → Camera → Formats → **Most Compatible**, or `pip install pillow-heif` |
| "Is another program using port 8000?" | Close the other program, or change `PORT` in `settings.py` |
| Want a clean start | Owner page → **Reset for a new demo**, or delete the `data/` folder |

Run the tests with `pip install -r requirements-dev.txt` then `pytest`.
