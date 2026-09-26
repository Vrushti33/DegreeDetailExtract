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

## Round 2 fixes (naming collision + free-tier robustness)

After shipping the first v4 patch, a naming problem was caught: the notebook
still saved everything to `checkpoints_v3` / `dataset_v3` paths on Drive —
identical to the original v3 run. Re-reading the *entire* notebook cell by
cell (not just the cells touched in round 1) to check for this turned up
several more real bugs, all now fixed:

1. **Path collision** — every dataset/checkpoint path renamed
   `..._v3` → `..._v4` throughout (dataset folder, dataset archive,
   checkpoint folder). Your original v3 dataset/checkpoints on Drive are
   left untouched, so you still have them for a "before" comparison in your
   report if you want one.
2. **Section 4 (Resume) had its own, independent copy of `build_target()`**
   that I'd missed patching in round 1 — it still had the broken closing tag.
   Since Colab free tier disconnects are common, this cell runs often; left
   unfixed, a resumed run would have silently reintroduced the original bug.
3. **False-positive "dataset is complete" check.** The old check
   (`count >= 1000`) would wrongly treat an interrupted generation run as
   finished, since generation writes records incrementally and a partial run
   easily exceeds 1000 while still being far short of the full ~4,000 train
   records. Free tier makes this a real risk (generation takes 18–28 min).
   Now checks against ~3,920 (98% of the expected 4,000) instead. Applied to
   both Section 2 and Section 4's dataset-restore logic.
4. **Section 7's fine-tune cell wasn't self-contained** — it referenced a
   variable (`REAL_BASE`) defined only in the previous cell, so it would
   break with a confusing error if run after a disconnect or run standalone.
   Now redefines everything it needs itself, matching the pattern already
   used by every other major cell in the notebook. Also added a clear error
   if the real-labeled training set ends up empty.
5. **Optimizer/scheduler state now persists across resumes.** Previously,
   every time Section 4 ran (likely more than once per training run on free
   tier), it restarted the cosine LR schedule from scratch over just the
   remaining epochs instead of continuing the original one. Checkpoints now
   save `optimizer.pt`/`scheduler.pt`, and Section 4 restores them when
   present.
6. **Free-tier Drive quota risk from fix #5.** Saving full AdamW optimizer
   state every epoch is expensive — roughly 1.6GB per save (about 2x the
   model weights, since Adam keeps two moment buffers per parameter).
   Unpruned, 10 epochs would have used **~24GB**, blowing past a free
   Google account's 15GB total quota (shared with Gmail/Photos) by itself.
   Fixed with a retention policy: only the most recent epoch keeps its
   optimizer/scheduler state (the only one ever resumed from); epoch model
   folders older than the last 2 are deleted (verified with a simulated
   10-epoch run); and the `best/` copy has its optimizer state stripped
   entirely, since it's only ever used for inference. Estimated peak usage
   is now **~5–6GB** for a full run.

All of these were verified, not just reasoned about: the tag-building/regex
round-trip was executed against a realistic sample record, every code cell
was syntax-checked, and the pruning logic was run against a simulated
10-epoch checkpoint sequence to confirm it keeps exactly what's needed and
nothing more.

## Round 3 fixes (based on your actual completed training run)

You ran the full pipeline (10 epochs across 3 disconnects, real fine-tuning,
real evaluation) and shared the output notebook. Here's what it showed and
what was fixed as a result.

**Section 5 (synthetic) is genuinely good news**: 87.5-99.5% exact match
across fields. The open-vocabulary fix from round 1 worked — the model
learned to read rather than memorize.

**Section 3 training overfit after epoch 3**, confirmed directly from your
logs: val_loss bottomed out at 0.1734 (epoch 3) and got steadily worse every
epoch after (0.1861 → 0.1951 → 0.2039 → 0.2070 by epoch 10), while train_loss
kept collapsing toward zero (0.0215). Your checkpointing correctly kept
epoch 3 as `best/`, so this didn't corrupt your results — just confirms
epochs 4-10 of synthetic training added no value and could be shortened in
future runs (not changed here since it didn't cause harm).

**The real problem: Section 7's real-data fine-tuning barely trained at
all.** Its loss only moved from 3.28 to 1.96 over 6 epochs — compare that to
synthetic training's loss dropping from 3.09 to 0.22 in a *single* epoch.
This directly explains Section 8's real-world results (0% exact match on
student_name, authority_name, and issue_date; CER over 100% on some fields,
meaning outright hallucination, not near-misses).

**Root causes, all now fixed in `cell-s7-finetune-real`:**
1. **LR was `2e-6`** — fine for a small nudge, far too conservative to adapt
   to a genuinely different visual domain from only 26 examples. Raised to
   `1e-5`.
2. **Only 6 epochs** — with 26 examples that's ~78 total gradient steps,
   nowhere near enough signal. Now runs up to 40 epochs, with early stopping
   based on real held-out loss (so it won't blindly run all 40 if it's
   already converged or starting to overfit).
3. **No augmentation on the real images** — meant there was no safe way to
   train longer without pure memorization. Now applies the repo's existing
   `generator/augment.py` pipeline (already used for synthetic generation,
   so it's proven to work with whatever albumentations version Colab
   installs) to the real training images only.
4. **No synthetic "replay"** — training on real-only risked forgetting the
   general reading ability from the synthetic stage while barely adapting.
   Now mixes in ~3x as many synthetic examples per epoch (drawn fresh from
   your existing `dataset_v4`) alongside the real ones.
5. **Checkpoint selection was "whatever epoch 6 happens to be"** rather than
   the actual best epoch. Now saves whichever epoch has the lowest real
   held-out loss, which could be well before epoch 40.

**Also fixed (didn't cause damage this run, but was a real bug):** Section 4
was reading "best val_loss so far" from the *latest* epoch's own metadata
rather than from the actual `best/` checkpoint's metadata. Since your run's
latest-at-each-resume-point happened to still be at-or-near the true best
each time, this didn't corrupt anything here — but it's a real risk in
general (a later, genuinely worse epoch could silently overwrite a better
earlier one), so it's fixed for future runs.

### Realistic expectations for your 1-week deadline

33 real labeled certificates (26 train / 7 eval) is a small dataset. The
fixes above will make training actually work instead of barely moving, but
don't expect near-100% real-world accuracy from this alone — with this little
data, results will likely still be strongest on fields with simpler/more
templated structure (course_name, pass_class) and weaker on free-text fields
(student_name, authority_name), and will vary a lot on universities/layouts
not resembling anything in your 26 training examples.

Two things worth doing if you have any spare time this week, in priority
order:
1. **Label a few more real certificates if you can get them** — even 10-15
   more, especially from different universities/layouts than what you
   already have, helps more than any hyperparameter tuning at this data
   scale.
2. **Double-check labeling consistency** across your 33 rows, especially for
   `specialization` and `pass_class` — with such a small, manually-entered
   set, one inconsistent convention (e.g. sometimes writing "N/A" vs leaving
   `""` for no specialization) measurably hurts training and looks like a
   model failure when it's actually a label-quality issue.

Re-run Section 7 (now fixed) and Section 8. Report both the Section 5 and
Section 8 tables together — a synthetic accuracy that's strong, a real
accuracy that's honestly weaker but meaningfully improved by domain
adaptation, and a clear explanation of why (small real dataset, and what
you'd do with more time/data) is a legitimate, complete story for an ML
class under a real deadline. That's a better project outcome than a project
that quietly reports only the flattering synthetic numbers.

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
