# Project Context: University Degree Certificate Field Extraction

## 1. Project Overview

**Goal:** Build a system that accepts an image of a university degree certificate and returns structured, machine-readable data for the following fields:

- `student_name`
- `university_name`
- `course_name`
- `specialization`
- `pass_class` (e.g., First Class, Distinction, Second Class, Pass)
- `authority_name` (signing authority / registrar / vice-chancellor etc.)
- `issue_date`

**Context:** This is an ML class project. The core deliverable for grading is a **fine-tuned transformer model** with a proper training pipeline, evaluation metrics, and reproducible results — not just an API wrapper around an existing service. A working web app (frontend + backend + deployment) is the stretch goal / final packaging layer, built after the model is validated.

**Target property:** The model should **generalize across university certificate layouts**, not just memorize a handful of templates seen during training.

---

## 2. Model Architecture Decision

### Chosen model: Donut (`naver-clova-ix/donut-base`)

**What it is:** Document Understanding Transformer — OCR-free, end-to-end. Swin Transformer image encoder → BART-style autoregressive text decoder. No separate OCR engine required at inference time.

**Why chosen over alternatives:**

| Approach | Pros | Cons | Verdict |
|---|---|---|---|
| **Donut** | Single model, image → structured JSON directly. Matches deployment story cleanly (one forward pass). Proven on structurally similar tasks (receipts/invoices/forms). | Generative — can occasionally hallucinate fields on unfamiliar layouts. Needs image+JSON pairs for training. | **Selected** |
| LayoutLMv3 | Layout-aware, well-documented for KIE tasks, more "explainable" (token classification). | Requires a separate OCR step (Tesseract/EasyOCR) at both train and inference time — two-stage pipeline. | Good candidate for a comparison/baseline experiment if time allows, not primary model. |
| Vision LLM API (GPT-4V/Claude) | Best raw accuracy, zero training needed. | Not a "trained model" — doesn't satisfy ML class requirement. Not free/offline. | Rejected for this class (was the original approach before pivoting to ML-class requirements). |
| Classic OCR + spaCy NER | Fully open-source, well understood. | Weaker on stylized/calligraphy fonts common on certificates; ignores layout/visual cues entirely. | Rejected in favor of Donut. |

**Task framing:** Treated as **document parsing / key information extraction (KIE)**. Training target is a JSON string per image, wrapped in Donut's task-token format, e.g.:

```
<s_cert><s_student_name>John Smith</s_student_name><s_university_name>XYZ University</s_university_name>...</s_cert>
```

---

## 3. Dataset Strategy

### 3.1 Why the originally proposed datasets were rejected

Three candidate datasets were evaluated and found unsuitable:

1. `kaggle.com/harikrish03/certificate-object-detectionsign-degrees-and-logo`
2. `roboflow.com/test-srvy4/university-certificates-uhuct`
3. `roboflow.com/document-processing/university-certificates`

**Findings:** All three are **object-detection** datasets (bounding boxes around regions like `Harvard-logo`, `Course Date`, `MIT`, `Year-number`) rather than **text key-value extraction** datasets. They mark *where* something is, not the *actual transcribed value* inside it. Donut requires image → JSON(value) pairs, which these datasets don't provide. They are also very small (57–191 images each) — insufficient volume even if the format matched.

**Disposition:** Not used as primary training data. Repurposed as a **supplementary visual asset source** (see 3.3).

### 3.2 Primary training data: synthetic certificate generation

Since no public dataset of real, transcribed university degree certificates exists (real certificates contain PII and aren't published in bulk for privacy/legal reasons), the primary dataset will be **synthetically generated**, with full control over field diversity and layout variety — directly supporting the generalization goal.

**Generation pipeline:**
- **Faker** — generates randomized realistic values: student names, dates, institution-style names.
- **Curated university name list** — mix of real public university names + fictional ones, to encourage the model to key off structural/contextual cues rather than memorizing a fixed set of known institutions.
- **Pillow / HTML+CSS rendering (via headless browser screenshot, e.g. Playwright)** — renders text onto certificate templates. HTML/CSS rendering preferred over raw Pillow for layout richness (borders, seals, multi-column text, varied typography).
- **≥15 distinct template layouts** — varying position of fields, font families, border/seal styles, orientation of institution name/logo block, wording variants for `pass_class` and degree phrasing (e.g., "Bachelor of Technology" vs "B.Tech." vs "Bachelor's Degree").
- **Albumentations** — post-render image augmentation: rotation/skew, noise, blur, brightness/contrast jitter, JPEG compression artifacts — to simulate photographed/scanned real-world uploads rather than clean renders only.
- Every generated image has **known ground-truth JSON** automatically, since the generator placed the values — no manual labeling required.

**Volume target:** *(TBD — pending confirmation; placeholder assumption: ~3,000–5,000 generated images, train/val/test split ~80/10/10, stratified to ensure balanced coverage of `pass_class` values and template layouts.)*

### 3.3 Supplementary data: real visual assets

- Real logo crops (Harvard, MIT, Caltech, Penn, UC, etc.) extracted from the Roboflow datasets' bounding-box regions — composited onto synthetic templates for visual realism.
- Real certificate photos from the three datasets used as **unlabeled reference material** for augmentation style calibration (lighting, paper texture, photo angle) — not used as labeled training targets.

### 3.4 Pipeline validation dataset: CORD

Before training on synthetic certificate data, the training pipeline will first be smoke-tested on **CORD** (`naver-clova-ix/cord-v2`, HuggingFace) — the standard Donut fine-tuning benchmark dataset (structured receipt key-value data). This isolates "is the training pipeline implemented correctly" from "is the certificate data itself good," which is a much easier debugging position.

---

## 4. Environment & Tooling

| Component | Choice |
|---|---|
| Training platform | **Google Colab** (GPU tier: *TBD — free T4 vs Colab Pro A100/V100, affects batch size and session length planning*) |
| Framework | **PyTorch 2.9.1** |
| CUDA | Colab-provided (typically 12.x; confirmed at runtime via `torch.version.cuda` — earlier "CUDA 130" reference needs clarification, will auto-detect rather than hardcode) |
| Core libraries | `transformers`, `datasets`, `accelerate`, `sentencepiece` |
| Data generation | `Faker`, `Pillow`, `Playwright` (HTML→image rendering), `Albumentations` |
| Evaluation | `scikit-learn` (metrics), `seqeval`-style field-level scoring, edit-distance/CER for free-text fields |
| Model serving (later phase) | `FastAPI` |
| Frontend (later phase) | `React` |
| Deployment (later phase) | Vercel (frontend) + Railway (backend/model serving) |

---

## 5. Training Plan

1. **Environment setup** — Colab notebook, install dependencies, verify GPU/CUDA availability, load `naver-clova-ix/donut-base` + `DonutProcessor`.
2. **Pipeline smoke test** — fine-tune briefly on CORD to confirm the training loop, tokenization, and generation/decoding all work correctly end-to-end.
3. **Synthetic data generation** — build and run the certificate generator; produce the full image + JSON-label dataset; upload to Google Drive or push as a HuggingFace dataset for reproducible Colab access.
4. **Fine-tuning on synthetic certificates** — `VisionEncoderDecoderModel` fine-tuning via `Seq2SeqTrainer` (or custom loop), task-token-wrapped JSON targets, mixed precision (fp16) for Colab GPU efficiency.
5. **Evaluation:**
   - Field-level exact-match accuracy per field (7 fields)
   - Character Error Rate (CER) for free-text fields (`student_name`, `university_name`, `course_name`, `authority_name`)
   - Confusion analysis for `pass_class` (closed-set field — should behave close to classification accuracy)
   - Qualitative check: run on real (non-synthetic) certificate photos from the Roboflow/Kaggle sets to sanity-check real-world generalization, even without full ground truth for all fields
6. **Checkpoint management** — save best model (by validation field-level F1) to Drive/HF Hub.
7. **Local inference validation** — script to load the fine-tuned model and run inference on a single image, supporting both CPU and CUDA, confirming output JSON schema is always well-formed (all 7 keys present, empty string if a field is missing/illegible).

**Out of scope for this phase:** FastAPI server, React frontend, and Vercel/Railway deployment — these come after the model is trained and locally validated.

---

## 6. Output Schema Contract

Every inference call must return exactly this JSON shape (empty string for missing/illegible fields — never omit a key):

```json
{
  "student_name": "",
  "university_name": "",
  "course_name": "",
  "specialization": "",
  "pass_class": "",
  "authority_name": "",
  "issue_date": ""
}
```

---

## 7. Open Items / Decisions Pending Confirmation

These are flagged rather than assumed, since they materially affect the data generator and training config:

1. **`pass_class` fixed value set** — exact list of labels to support (e.g., "First Class", "First Class with Distinction", "Second Class Upper", "Pass") — needed to build the synthetic generator's vocabulary for this field.
2. **Synthetic dataset size** — target number of generated images (affects Colab training time and generator scope).
3. **Colab tier** — free vs Pro (affects GPU memory, batch size, image resolution, and session-length-driven checkpointing strategy).
4. **Held-out real-world test set** — whether a small manually-verified set of real certificate images (even without full training-scale labels) will be assembled to sanity-check generalization beyond synthetic data, and if so, how many / from where.

---

## 8. Project Phases Summary

| Phase | Status |
|---|---|
| 1. Problem definition & tech stack decisions | ✅ Complete |
| 2. Model architecture selection (Donut) | ✅ Complete |
| 3. Dataset strategy (synthetic + supplementary) | ✅ Complete |
| 4. Synthetic certificate generator build | 🔜 Next |
| 5. Colab environment setup + CORD pipeline smoke test | Pending |
| 6. Fine-tuning on synthetic data | Pending |
| 7. Evaluation & metrics reporting | Pending |
| 8. Local inference validation (CPU/CUDA) | Pending |
| 9. FastAPI backend | Not started (future phase) |
| 10. React frontend | Not started (future phase) |
| 11. Deployment (Vercel/Railway) | Not started (future phase) |
