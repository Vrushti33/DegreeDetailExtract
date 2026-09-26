# DegreeDetailExtract — Web App Build Notes

This documents what was built in response to "build backend + frontend now,
in parallel with any further model tuning you do": a FastAPI backend and a
React frontend, delivered as `degree-extract-webapp.zip`. It covers what was
done, why each decision was made, and — the important part — exactly how to
connect this app to your properly-trained model once it's ready.

---

## 1. What was built

### Backend (`backend/`)
- **`main.py`** — a FastAPI service with one real endpoint, `POST /extract`.
  It loads the Donut processor + model once at startup, and on each request:
  validates the upload (file type, size), runs the same generate-and-parse
  inference logic as the notebook's Section 6, and returns the 7 fields as
  JSON plus a list of any fields that came back empty.
- **`requirements.txt`** — pinned versions for FastAPI, Uvicorn, PyTorch,
  Transformers, SentencePiece, Pillow.
- **`Dockerfile`** — installs a CPU-only PyTorch wheel separately from the
  rest of requirements (keeps the image smaller and the build more
  reliable), then runs Uvicorn. Railway auto-detects this.
- **`README.md`** — how to get your model out of Colab, run locally, and
  deploy to Railway.

### Frontend (`frontend/`)
- A Vite + React + Tailwind single-page app.
- **`src/App.jsx`** — the entire UI: a drag-and-drop upload zone, an image
  preview with a status line, and a results "ledger" card that reveals once
  the backend responds.
- Config files (`vite.config.js`, `tailwind.config.js`, `postcss.config.js`,
  `index.html`) and a `README.md` covering local run + Vercel deployment.

### Top-level `README.md`
Ties the two together and states the order of operations (finish model →
push to Hub → run both locally → deploy both).

Both pieces were tested before delivery, not just written: the frontend was
actually built with `npm install && npm run build` (succeeded, no errors),
and the backend was syntax-checked (`py_compile` + an AST parse to confirm
all route functions are defined correctly). A Python 3.9-compatibility issue
(`X | None` type-hint syntax needing Python 3.10+) was caught and fixed with
`from __future__ import annotations`.

---

## 2. Decisions made, and why

### Why FastAPI serves exactly one endpoint, not a full API
The project's actual job is "upload an image, get fields back." Adding
endpoints for things like history, auth, or multiple models would be scope
the project doesn't need yet and would cost time you don't have this week.
`/health` exists only so you can quickly confirm the model finished loading
before testing `/extract`.

### Why the model loads from HuggingFace Hub, not from a local file or Google Drive
This was the least obvious design decision, so it's worth explaining in
full — see Section 3 below, since it's also the answer to "how do I connect
my trained model." Short version: Railway (and most free hosting) can't
reach your personal Google Drive, and the checkpoint (~800MB) is too large
to commit to a git repo. The Hub is the one place `from_pretrained()`
already knows how to pull from with no extra code, and it's free for a
private repo.

### Why CORS is configured through an environment variable, not hardcoded
`ALLOWED_ORIGINS` defaults to `localhost:5173` for local development, but
you'll need to add your real Vercel URL once deployed. Making it an env var
means you change a setting on Railway rather than editing and redeploying
code.

### Why upload validation exists (content-type check, 15MB limit)
Without it, a non-image file reaching `Image.open()` produces a raw 500
error with a Python traceback — fine for you during development, confusing
for anyone else opening the app (including whoever grades this). The
validation turns that into a plain-language error message instead.

### Why the frontend has no component library or extra state library
Just React state and `fetch`. For a project you need to hand in and explain
in a week, fewer dependencies means fewer things that can break in ways
unrelated to your actual project, and less unfamiliar code to explain if
asked about it.

### Why this particular visual design
Per the design guidance this environment uses for new UI work, a distinctive
design should be grounded in the actual subject matter rather than reaching
for generic defaults. The subject here is a physical paper certificate with
an official seal — so the design leans into that directly: a dark
"registrar's office" shell around a warm parchment-toned results card, a
wax-seal mark as the one recurring icon, and rule-line dividers between
fields instead of the generic boxed-card-with-shadow treatment. Deliberately
avoided: the cream-background-plus-terracotta-accent look and the
identical-rounded-card SaaS pattern, both called out as common AI-generated
design tells rather than actual choices. This is a styling layer only —
restyle `App.jsx` freely if you want a different look; none of the
extraction logic lives in the styling.

### Why Railway + Vercel specifically
This matches what was already decided earlier in the project (Section 1 of
this project's original tech-stack discussion): FastAPI backend, React
frontend, Vercel/Railway deployment. Nothing new introduced here.

---

## 3. Exact next steps: connecting your properly-trained model

This is the part that actually matters for your deadline. The app currently
has no model attached to it — it's built to receive one. Here's precisely
what to do, once you're done iterating in the notebook:

### Step 1 — Finish deciding on a final checkpoint
Keep running the Section 7 → Section 8 loop (fine-tune on real data, check
real held-out accuracy) until either you're satisfied or you're running low
on time. Whichever checkpoint has the best Section 8 numbers is your final
model — usually `checkpoints_v4_real_ft/best`, or `checkpoints_v4/best` if
the real fine-tuning didn't end up helping enough to keep.

### Step 2 — Push that checkpoint to HuggingFace Hub
Still inside the Colab notebook, after loading that final checkpoint into
`processor`/`model` variables (Section 5 or 6's loading cells already do
this), run:

```python
from huggingface_hub import login
login()  # paste a token from https://huggingface.co/settings/tokens (needs "write" access)

REPO_ID = "your-username/degree-extract-donut"  # pick any name, keep it
processor.push_to_hub(REPO_ID, private=True)
model.push_to_hub(REPO_ID, private=True)
```

This uploads the model files to a private repo on huggingface.co. It takes
a few minutes (uploading ~800MB).

### Step 3 — Run the backend locally and confirm it loads your model
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export MODEL_SOURCE=your-username/degree-extract-donut
export HF_TOKEN=hf_xxxxxxxxxxxx      # a token with at least read access to that repo
export ALLOWED_ORIGINS=http://localhost:5173

uvicorn main:app --reload --port 8000
```
Visit `http://localhost:8000/health` and confirm `"model_loaded": true`.
Then test with a real image before touching the frontend at all:
```bash
curl -X POST http://localhost:8000/extract -F "file=@/path/to/certificate.jpg"
```
If this returns sensible JSON, your model is correctly wired in — everything
after this point is just deployment plumbing, not model logic.

### Step 4 — Run the frontend locally against it
```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL=http://localhost:8000 by default
npm run dev
```
Open `http://localhost:5173`, upload a real certificate photo, confirm the
ledger card shows sensible values.

### Step 5 — Deploy the backend to Railway
Push `backend/` to GitHub, create a Railway project from that repo, and set
these three variables in Railway's dashboard (**Variables** tab):
- `MODEL_SOURCE = your-username/degree-extract-donut`
- `HF_TOKEN = hf_xxxxxxxxxxxx`
- `ALLOWED_ORIGINS = https://your-app.vercel.app` (you'll get this URL in
  Step 6 — you can come back and update this after)

Railway detects the `Dockerfile` automatically and builds/deploys. Copy the
public URL it gives you (something like
`https://your-service.up.railway.app`).

### Step 6 — Deploy the frontend to Vercel
Push `frontend/` to GitHub, import it into Vercel, and set:
- `VITE_API_URL = https://your-service.up.railway.app` (the URL from Step 5)

Deploy. Then go back to Railway and make sure `ALLOWED_ORIGINS` matches the
exact Vercel URL you were just given — this is the step people most often
forget, and the symptom is a CORS error in the browser console with an
otherwise-working backend.

### How to swap in a better model later (e.g. after labeling more real data)
You never touch backend or frontend code for this. Just:
1. Repeat Step 2 (`push_to_hub` again to the same `REPO_ID` — this
   overwrites the repo with the new weights).
2. Restart the Railway service (or just wait — it reloads the model at
   startup, so any restart picks up the new version automatically).

That's the entire update path: retrain → push_to_hub → restart backend.

---

## 4. Quick pre-submission checklist

- [ ] `/health` on the deployed backend shows `"model_loaded": true`
- [ ] A real certificate photo, uploaded through the deployed frontend,
      returns a sensible (if imperfect) result — not an error
- [ ] `ALLOWED_ORIGINS` on Railway exactly matches your live Vercel URL
- [ ] Your report includes both the Section 5 (synthetic) and Section 8
      (real) accuracy tables, with an honest note on the real dataset's
      small size as the main limiting factor
