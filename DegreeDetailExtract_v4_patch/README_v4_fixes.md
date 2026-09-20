# DegreeDetailExtract v4 — Diagnosis & Fixes

## What was actually wrong

Your v3 model's bad real-world output (`"University of California, George..."`,
`"President, John"`, missing `pass_class`) was **not** a training-loop bug and
**not** primarily an image-orientation bug (I initially suspected the
`do_align_long_axis=False` setting, but checked the actual pixel dimensions —
your real test image is 466×659 (ratio 0.707) and the synthetic canvas is a
fixed 1000×1400 (ratio 0.714), nearly identical, so that wasn't the main cause
here — re-enabled it anyway below since it's still a real robustness gap for
*other* real-world uploads).

**The real cause, confirmed by reading your actual generator code
(`generator/faker_fields.py`):**

1. **`university_name` was `random.choice()` from a fixed list of 85 names.**
   Across 5,500 training images, each name was seen ~65 times on average —
   few enough that the model could simply memorize "pick the closest of these
   85 strings" instead of learning to read arbitrary text. "University of
   Calicut" was not in that list at all, so the model could not extract it —
   it blended memorized names with fragments it did read correctly.
2. **`authority_name` was *always* built as `f"{title}, {name}"`** from a
   13-item title list — a single rigid shape across 100% of training
   examples. The model learned that shape as a rule, not something read from
   the image. `"President, John"` is exactly that memorized shape filled with
   a common fake name, not anything read from the real signature block.
3. **`pass_class` had 14 fixed values, and "Third Class" was not one of
   them.** Guaranteed miss on this certificate regardless of anything else.
4. **Section 5's evaluation metrics only test on the same closed-vocabulary
   synthetic distribution as training**, so good-looking numbers there tell
   you nothing about real-world readiness — this is the same trap that bit
   v1 ("94-100% synthetic, failed badly on real certs").
5. **Zero real images were ever in the training set.** The 23 real
   certificates were only used to extract background paper textures — the
   model has never seen real fonts, seals, or layouts with correct labels.
6. **Minor bug:** the training-target builder closed tags as `</field>`
   while the special tokens registered with the tokenizer were
   `</s_field>` — a mismatch that wasted the added vocabulary slots (fixed,
   see below; low-impact but worth cleaning up).

## What changed

### `generator/faker_fields.py`
- `PASS_CLASSES` expanded to include Third Class, Third/Second/First
  Division, Class II Division I/II, Pass Class, etc.
- New `_random_university_name()`: ~50% from the curated list (for
  realistic *style*), ~50% procedurally generated and never repeated
  (`University of {city}`, `{name} Institute of Technology`, etc.) — this is
  the single highest-impact change. It forces the model to actually read
  pixels instead of picking from a memorized shortlist. Verified locally:
  1,000 unique names out of 2,000 samples generated (vs. a hard cap of 85
  before).
- New `_random_authority_name()`: 6 different formats (title-only,
  name-only, "Title, Name", "Name, Title", "Name (Title)") instead of one
  rigid shape every time.

### `DegreeDetailExtract_v4.ipynb`
- **Fixed** the `build_target()` / regex closing-tag mismatch throughout
  (dataset-building cell, both Section 5 eval cells, Section 6 inference
  cell) — now consistently `</s_{field}>` everywhere, matching the tokens
  actually registered with the tokenizer.
- **Re-enabled** `processor.image_processor.do_align_long_axis = True` for
  robustness against real-world photos with unusual aspect ratios/orientation
  (didn't cause this specific failure, but is still a latent risk).
- **Added a clear warning** in Section 2 that the dataset MUST be
  regenerated (the "Force v4 dataset regeneration" cell already existed in
  your notebook — now it's clearly flagged as required, not optional, since
  the vocabulary changes only take effect in freshly generated data).
- **Added Section 7 — Real-Certificate Domain Adaptation**: fine-tunes your
  best synthetic checkpoint on a small set of manually labeled real
  certificates (low LR, few epochs — standard practice for closing a
  synthetic→real domain gap without needing thousands of real images).
- **Added Section 8 — Honest Real-World Evaluation**: runs the same
  field-exact-match/CER metric as Section 5, but on real, held-out
  certificates never seen in training. This is the number to actually trust
  and report.

## What you need to do

1. **Re-run Section 2's "Force v4 dataset regeneration" cell, then Section
   2's generation cell.** Skipping this means you're still training on the
   old closed-vocabulary data and none of the fixes take effect.
2. **Run Section 3 (training) fresh** — the vocabulary and tag fixes mean
   old checkpoints aren't directly comparable; a clean retrain is safest for
   your project's reported numbers.
3. **Before Section 7:** manually label 15–30 real certificate images
   (instructions are in the notebook's Section 7 markdown cell) and upload
   them + a `metadata.jsonl` to Google Drive at
   `DegreeDetailExtract/real_labeled/`.
4. **Run Section 7**, then **Section 8** to get your honest real-world
   accuracy numbers.
5. **In your report**, present both the Section 5 (synthetic) and Section 8
   (real) tables together — the gap between them, and how domain adaptation
   narrows it, is a legitimate and genuinely interesting result for an ML
   class, not something to hide.

## What this doesn't fix (things to consider if accuracy is still weak after this)

- **Visual style gap**: your synthetic templates use abstract shapes as
  logo placeholders; real certificates often have ornate seals/crests and
  gothic-script banners. If Section 8 numbers are still weak after domain
  adaptation, consider adding real seal/crest image overlays and more
  ornate banner-text templates to the generator.
- **Schema ambiguity**: some real certificates report per-part results
  (e.g. "Third Class" separately for three subject parts) rather than one
  overall class — decide and document a consistent labeling convention for
  your real-labeled data (see the note in Section 7).
