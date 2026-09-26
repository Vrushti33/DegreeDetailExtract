# DegreeDetailExtract — Backend

A small FastAPI service with one real endpoint: `POST /extract`. Upload a
degree certificate image, get back the 7 extracted fields as JSON.

## 1. Get your trained model out of Colab

Your checkpoint lives on Google Drive right now
(`checkpoints_v4_real_ft/best`, or `checkpoints_v4/best` if you didn't run
the real fine-tuning). The backend can't read your Google Drive, so the
model needs to live somewhere it can load from at startup. The easiest path
is a **private HuggingFace Hub model repo** — free, and `from_pretrained()`
already knows how to pull from it directly (no extra code beyond what's in
`main.py`).

Run this **once, in your Colab notebook**, after loading whichever
checkpoint you've decided is final:

```python
from huggingface_hub import login
login()  # paste a token from https://huggingface.co/settings/tokens (needs "write" access)

REPO_ID = "your-username/degree-extract-donut"  # pick any name
processor.push_to_hub(REPO_ID, private=True)
model.push_to_hub(REPO_ID, private=True)
```

Then set two environment variables when running the backend (locally or on
Railway):

- `MODEL_SOURCE` = `your-username/degree-extract-donut`
- `HF_TOKEN` = a HuggingFace token with **read** access to that repo (only
  needed because the repo is private — if you instead push with
  `private=False`, you can drop this variable entirely)

If you'd rather not use the Hub at all, you can instead download the
checkpoint folder from Drive and place it at, e.g., `backend/model/`, then
set `MODEL_SOURCE=./model`. This works fine locally but is impractical for
most free hosting platforms (the checkpoint is ~800MB, too big to commit to
git) — the Hub approach is the one to use for actually deploying.

## 2. Run locally

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

export MODEL_SOURCE=your-username/degree-extract-donut
export HF_TOKEN=hf_xxxxxxxxxxxx          # only if the repo is private
export ALLOWED_ORIGINS=http://localhost:5173

uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/health` — you should see
`{"status": "ok", "model_loaded": true, ...}` once the model finishes
loading (can take 10-30 seconds the first time).

Test the endpoint directly without the frontend:

```bash
curl -X POST http://localhost:8000/extract \
  -F "file=@/path/to/a/certificate.jpg"
```

## 3. Deploy to Railway

1. Push this `backend/` folder to a GitHub repo (or a subfolder of your
   existing one — Railway lets you set a root directory).
2. On [railway.app](https://railway.app), "New Project" → "Deploy from
   GitHub repo" → select this repo/folder. Railway will detect the
   `Dockerfile` automatically.
3. In the service's **Variables** tab, add:
   - `MODEL_SOURCE` = `your-username/degree-extract-donut`
   - `HF_TOKEN` = your token (if the repo is private)
   - `ALLOWED_ORIGINS` = the URL your frontend will be deployed at (e.g.
     `https://your-app.vercel.app`) — comma-separate multiple origins if
     needed
4. Deploy. Railway gives you a public URL like
   `https://your-service.up.railway.app` — this is what the frontend's
   `VITE_API_URL` should point to.

**Note on cost/speed:** this model runs on CPU by default on most free
hosting tiers (Railway's free tier has no GPU). Inference on CPU typically
takes a few seconds per image, which is fine for a demo but noticeably
slower than the GPU inference you saw in Colab — this is expected, not a
bug.

## API reference

### `GET /health`
Returns `{"status": "ok", "model_loaded": bool, "device": "cpu"|"cuda"}`.

### `POST /extract`
Multipart form upload, field name `file`. Accepts JPEG/PNG/WebP, max 15MB.

Response:
```json
{
  "fields": {
    "student_name": "...",
    "university_name": "...",
    "course_name": "...",
    "specialization": "...",
    "pass_class": "...",
    "authority_name": "...",
    "issue_date": "..."
  },
  "missing_fields": ["pass_class"]
}
```
`missing_fields` lists any field the model returned empty — the frontend
uses this to show "not detected" instead of a blank space.
