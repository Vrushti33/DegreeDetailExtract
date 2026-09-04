"""
DegreeDetailExtract — Local Demo App
=====================================
Run:  python app.py
Then: browser opens automatically at http://localhost:7860
"""

import re
import json
import time
import torch
import gradio as gr
from pathlib import Path
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel

# ── Configuration ──────────────────────────────────────────────────────────────
MODEL_DIR = Path("checkpoints/best_model")
DEVICE    = "cuda" if torch.cuda.is_available() else "cpu"

FIELDS = [
    "student_name",
    "university_name",
    "course_name",
    "specialization",
    "pass_class",
    "authority_name",
    "issue_date",
]

LABELS = {
    "student_name":    "🎓  Student Name",
    "university_name": "🏛️  University",
    "course_name":     "📖  Degree / Course",
    "specialization":  "🔬  Specialization",
    "pass_class":      "🏅  Class Awarded",
    "authority_name":  "✍️  Signing Authority",
    "issue_date":      "📅  Issue Date",
}

# ── Load model at startup ──────────────────────────────────────────────────────
if not MODEL_DIR.exists():
    raise FileNotFoundError(
        f"\n\n❌  Model not found at: {MODEL_DIR.resolve()}\n\n"
        "Please download it from Google Drive first:\n"
        "  Drive → MyDrive / DegreeDetailExtract / checkpoints / best_model\n"
        "Place the folder at:  checkpoints/best_model\n"
        "Then re-run:  python app.py\n"
    )

print(f"📦  Loading model on {DEVICE.upper()} ...")
t0        = time.time()
processor = DonutProcessor.from_pretrained(MODEL_DIR)
model     = VisionEncoderDecoderModel.from_pretrained(MODEL_DIR, torch_dtype=torch.float32)
model.to(DEVICE).eval()
print(f"✅  Model ready in {time.time() - t0:.1f}s\n")

# ── Inference ──────────────────────────────────────────────────────────────────
def decode_fields(sequence: str) -> dict:
    result = {}
    for key in FIELDS:
        m = re.search(rf"<s_{key}>(.*?)</s_{key}>", sequence, re.DOTALL)
        result[key] = m.group(1).strip() if m else ""
    return result


def run_inference(image: Image.Image) -> tuple[dict, float]:
    pixel_values = processor(
        image.convert("RGB"), return_tensors="pt"
    ).pixel_values.to(DEVICE)

    t0 = time.time()
    with torch.no_grad():
        outputs = model.generate(
            pixel_values,
            decoder_input_ids=torch.tensor(
                [[model.config.decoder_start_token_id]]
            ).to(DEVICE),
            max_length=512,
            early_stopping=True,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=1,
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
            return_dict_in_generate=True,
        )
    elapsed = time.time() - t0

    seq = processor.tokenizer.batch_decode(outputs.sequences)[0]
    seq = (
        seq.replace(processor.tokenizer.eos_token, "")
           .replace(processor.tokenizer.pad_token, "")
    )
    return decode_fields(seq), elapsed


# ── Gradio handler ─────────────────────────────────────────────────────────────
def extract(image):
    if image is None:
        blanks = ["—"] * len(FIELDS)
        return *blanks, {}, "Upload a certificate image and click Extract."

    pil = image if isinstance(image, Image.Image) else Image.fromarray(image)
    fields, elapsed = run_inference(pil)

    values  = [fields.get(f, "") or "—" for f in FIELDS]
    json_out = {**{k: "" for k in FIELDS}, **fields}
    status   = (
        f"✅  Extraction complete in **{elapsed:.1f}s** "
        f"on {DEVICE.upper()}  |  "
        f"{sum(1 for v in fields.values() if v)} / {len(FIELDS)} fields found"
    )
    return *values, json_out, status


# ── UI ─────────────────────────────────────────────────────────────────────────
CSS = """
body { font-family: 'Segoe UI', sans-serif; }
.title-bar  { background: linear-gradient(135deg,#1a237e,#283593);
              padding:18px 28px; border-radius:12px; margin-bottom:16px; }
.title-bar h1 { color:#fff !important; margin:0; font-size:1.7rem; }
.title-bar p  { color:#90caf9 !important; margin:4px 0 0; }
.field-box textarea { font-size:1.05rem !important; font-weight:500 !important; }
.status-bar { background:#e8f5e9; border-left:4px solid #4caf50;
              padding:10px 16px; border-radius:6px; }
footer { display:none !important; }
"""

FIELD_IDS = [f"field_{f}" for f in FIELDS]

with gr.Blocks(title="DegreeDetailExtract", css=CSS) as demo:

    # Header
    gr.HTML("""
    <div class="title-bar">
      <h1>🎓 DegreeDetailExtract</h1>
      <p>AI-powered certificate field extractor &nbsp;·&nbsp;
         Fine-tuned Donut model &nbsp;·&nbsp;
         Upload → Extract → Done</p>
    </div>
    """)

    with gr.Row(equal_height=True):
        # ── Left: image upload ──────────────────────────────────────────────
        with gr.Column(scale=5):
            img_in = gr.Image(
                type="pil",
                label="Certificate Image",
                height=520,
                sources=["upload", "clipboard"],
            )
            btn = gr.Button("🔍  Extract Fields", variant="primary", size="lg")

        # ── Right: extracted fields ─────────────────────────────────────────
        with gr.Column(scale=5):
            gr.Markdown("### Extracted Fields")

            field_outputs = []
            for f in FIELDS:
                tb = gr.Textbox(
                    label=LABELS[f],
                    interactive=False,
                    elem_id=f"field_{f}",
                    container=True,
                )
                field_outputs.append(tb)

            gr.Markdown("---")
            json_out   = gr.JSON(label="JSON Output")
            status_out = gr.Markdown("Upload a certificate and click **Extract Fields**.")

    # Wire up
    outputs_list = [*field_outputs, json_out, status_out]

    btn.click(fn=extract, inputs=[img_in], outputs=outputs_list)
    img_in.change(fn=extract, inputs=[img_in], outputs=outputs_list)

    gr.Markdown("""
    ---
    **About this model**: Donut (Document Understanding Transformer) fine-tuned on 5,000 synthetic
    degree certificates across 22 diverse layout templates. Extracts 7 structured fields without
    any OCR preprocessing step.
    """)

if __name__ == "__main__":
    print("🚀  Starting DegreeDetailExtract demo ...")
    print(f"    Model : {MODEL_DIR.resolve()}")
    print(f"    Device: {DEVICE.upper()}")
    print()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True,
        show_error=True,
    )
