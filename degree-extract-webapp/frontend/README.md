# DegreeDetailExtract — Frontend

A small React (Vite + Tailwind) app: upload a degree certificate image, see
the extracted fields laid out as a certificate-style ledger.

## Run locally

Needs Node.js 18+.

```bash
cd frontend
npm install
cp .env.example .env    # edit VITE_API_URL if your backend isn't on localhost:8000
npm run dev
```

Open `http://localhost:5173`. Make sure the backend (see `../backend`) is
running first — the page will show a connection error otherwise.

## Deploy to Vercel

1. Push this `frontend/` folder to a GitHub repo (or a subfolder of your
   existing one — Vercel lets you set a root directory).
2. On [vercel.com](https://vercel.com), "Add New" → "Project" → import the
   repo. Vercel auto-detects Vite.
3. Under **Environment Variables**, add:
   - `VITE_API_URL` = your deployed backend's URL (e.g.
     `https://your-service.up.railway.app`) — no trailing slash.
4. Deploy. Vercel gives you a public URL.

Make sure the backend's `ALLOWED_ORIGINS` environment variable (see
`../backend/README.md`) includes this Vercel URL, or the browser will block
the requests with a CORS error.

## What's here

- `src/App.jsx` — the whole UI: a drag-and-drop upload zone on the left, and
  a results "ledger" card on the right that reveals once the backend
  responds.
- Talks to exactly one backend endpoint: `POST {VITE_API_URL}/extract`,
  multipart form field `file`. See `../backend/README.md` for the response
  shape.
- No component library or extra state-management dependency — just React
  state and `fetch`, to keep this easy to read and modify for a class
  project.
