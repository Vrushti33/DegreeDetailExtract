# DegreeDetailExtract — Web App

Upload a photo or scan of a university degree certificate; get the student
name, university, course, specialization, class/division, signing
authority, and issue date back as structured data.

This is the deployment layer for the Donut model trained in
`DegreeDetailExtract_v4.ipynb`. It does not contain any training code —
it just loads whichever checkpoint you decide is final and serves it.

```
backend/    FastAPI service — loads the model, exposes POST /extract
frontend/   React (Vite + Tailwind) — upload UI + results display
```

## Order of operations

1. **Finish model iteration first** (Section 7/8 loop in the notebook,
   as discussed). You need a checkpoint you're satisfied with before this
   part matters — the app is only as good as whatever model you point it at.
2. **Push that checkpoint to HuggingFace Hub** — see
   `backend/README.md` section 1 for the exact two lines of Colab code.
3. **Run the backend locally** — `backend/README.md` section 2. Confirm
   `/health` and a manual `/extract` call work before touching the frontend.
4. **Run the frontend locally** — `frontend/README.md`. Point it at your
   local backend and confirm the whole upload → result flow works.
5. **Deploy both** — `backend/README.md` section 3 (Railway) and
   `frontend/README.md` (Vercel). Deploy the backend first, so you have its
   URL to give the frontend.

## Design note

The visual design (in `frontend/src/App.jsx`) is deliberately built around
the actual subject matter — a physical paper certificate with an official
seal — rather than a generic dashboard look: a dark "registrar's office"
shell around a warm parchment-toned results card, brass rule-lines instead
of boxed cards for each field, and a wax-seal mark as the one recurring
motif. Feel free to restyle it; the field-parsing logic in `App.jsx` and
`main.py` is what actually needs to stay correct.
