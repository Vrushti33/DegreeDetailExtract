# Degree Certificate Detail Extraction (DegreeDetailExtract)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![HuggingFace Transformers](https://img.shields.io/badge/%F0%9F%A4%97%20Transformers-Donut-FFD21E?style=flat)](https://huggingface.co/docs/transformers/model_doc/donut)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React + Vite](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=flat&logo=react&logoColor=black)](https://vitejs.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> **B.Tech. Project-2 (Semester VII)**  
> **Author:** Shah Vrushti T. (ID: 23ITUOS122 / IT127)  
> **Supervisor:** Dr. Harshadkumar B. Prajapati, Professor, Department of Information Technology  
> **Institution:** Dharmsinh Desai University (DDU), Nadiad, Gujarat, India  

---

## 📌 Table of Contents
- [Overview](#-overview)
- [Why Donut (OCR-Free)?](#-why-donut-ocr-free)
- [System Architecture](#-system-architecture)
- [Target Fields](#-target-fields)
- [Repository Structure](#-repository-structure)
- [Semi-Synthetic Dataset Generation](#-semi-synthetic-dataset-generation)
- [Model Training & Iterations (v2 → v6)](#-model-training--iterations-v2--v6)
- [Web Application Setup](#-web-application-setup)
  - [Prerequisites](#prerequisites)
  - [Backend Setup (FastAPI)](#1-backend-setup-fastapi)
  - [Frontend Setup (React + Vite)](#2-frontend-setup-react--vite)
- [API Reference](#-api-reference)
- [Evaluation Results](#-evaluation-results)
- [License & Citation](#-license--citation)

---

## 📖 Overview

Academic degree certificates are highly heterogeneous documents characterized by ornate typography (Gothic / Old English scripts), embossed watermarks, institutional seals, bilingual text, and arbitrary spatial layouts. 

Traditional Information Extraction (IE) pipelines rely on **OCR + Heuristic Regex / LayoutLM**, which suffer from **cascading OCR failures**: if upstream OCR misreads decorative scripts or noisy backgrounds, downstream extractors fail completely.

**DegreeDetailExtract** implements an end-to-end, **OCR-free document understanding pipeline** powered by **Donut (Document Understanding Transformer)**. By mapping visual tokens directly to structured JSON tokens, the system accurately extracts candidate names, degree titles, universities, passing dates, classifications, and signing authorities, paired with a **Dual-Pass Tesseract OCR alignment engine** for dynamic visual bounding-box localization.

---

## ⚡ Why Donut (OCR-Free)?

| Challenge in Degree Certificates | Traditional OCR + Pipeline | Donut (Our Approach) |
| :--- | :--- | :--- |
| **Calligraphic / Gothic Scripts** | Upstream OCR produces garbled tokens | Vision encoder processes visual features directly |
| **Complex Watermarks & Seals** | OCR extracts background noise as fake characters | Multi-head self-attention focuses solely on semantic text |
| **Non-Standard Spatial Formats** | Rigid regex and fixed-grid rules shatter | Sequence-to-sequence decoder generates structured JSON |
| **Error Propagation** | Upstream errors permanently cascade downstream | Single unified model trained with end-to-end cross-entropy |

---

## 🏗 System Architecture

The project features a **Two-Stage Hybrid Inference Pipeline**:
1. **Stage 1 (Semantic Extraction)**: Donut reads certificate pixels directly and outputs clean structured JSON.
2. **Stage 2 (Spatial Localization)**: A parallel dual-pass OCR layer (Tesseract PSM 3 + PSM 11) performs fuzzy string alignment and spatial clustering to highlight each field on the certificate with an exact bounding box.

```
       ┌───────────────────────────────┐
       │   Degree Certificate Image   │
       └──────────────┬────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
┌───────────────────────┐   ┌──────────────────────────────┐
│  Stage 1: Donut Model │   │  Stage 2: Dual-Pass Tesseract│
│  (Swin-B + mBART)     │   │  (PSM 3 & PSM 11 Alignment)  │
└───────────┬───────────┘   └──────────────┬───────────────┘
            │ Structured                   │ Word Tokens &
            │ JSON Values                  │ Pixel Coordinates
            └─────────────┬────────────────┘
                          ▼
             ┌─────────────────────────┐
             │ Fuzzy String Matcher &  │
             │ Spatial Cluster Engine  │
             └────────────┬────────────┘
                          ▼
             ┌─────────────────────────┐
             │ Extracted JSON + BBoxes │
             │ & Interactive Web UI    │
             └─────────────────────────┘
```

---

## 🎯 Target Fields

The model extracts the following key academic metadata attributes:

- `<s_candidate_name>`: Full name of the candidate / graduate
- `<s_university>`: Conferrer institution / university name
- `<s_degree>`: Degree conferred (e.g., *Bachelor of Technology*, *Master of Science*)
- `<s_specialization>`: Major / Department (e.g., *Information Technology*)
- `<s_pass_class>`: Division, Grade, CGPA, Merit, or Honours classification
- `<s_authority_name>`: Signatory official (Chancellor, Vice Chancellor, Registrar)
- `<s_passing_year>` / `<s_issue_date>`: Date of conferral / passing vs. Date of certificate issue

---

## 📂 Repository Structure

```plaintext
DegreeDetailExtract/
├── checkpoints/                        # Model weights & tokenizer files
│   ├── best_model/                     # Active production checkpoint (v6)
│   └── best_model_6/                   # Checkpoint iteration v6
├── cert_fonts/                         # Gothic, Calligraphic & Serif fonts for synthesis
├── generator/                          # Procedural Certificate Generator Engine
│   ├── augment_v6.py                   # Photometric & geometric data augmentation
│   ├── date_utils.py                   # Date parser & normalizer (written-out & numeric)
│   ├── faker_fields.py                 # Open-vocabulary field synthesis (Names, Unis, Degrees)
│   ├── fonts.py                        # Typography loaders & fallbacks
│   └── templates_v4.py                 # 2D certificate layout renderers
├── real_certs/                         # Real scanned backgrounds & layout templates
├── degree-extract-webapp/              # Production Web Application
│   ├── backend/                        # FastAPI service (main_v6.py)
│   └── frontend/                       # React + Vite + TailwindCSS UI
├── generate_certificates_v4.py         # Full synthetic dataset generator CLI
├── generate_semi_synthetic_v6.py       # Semi-synthetic backdrop generator CLI
├── DegreeDetailExtract_v2.ipynb        # Training Notebook Iteration v2
├── DegreeDetailExtract_v4.ipynb        # Training Notebook Iteration v4
├── DegreeDetailExtract_v5.ipynb        # Training Notebook Iteration v5
├── DegreeDetailExtract_v6.ipynb        # Training Notebook Iteration v6 (Current)
├── requirements_local.txt              # Core Python dependencies
├── requirements_generator.txt          # Generator dependencies
└── README.md                           # Documentation
```

---

## 🧪 Semi-Synthetic Dataset Generation

Due to strict privacy considerations and scarcity of public diploma datasets, a high-fidelity synthetic generation pipeline was constructed:

```bash
# Generate 500 semi-synthetic certificates using real background scans:
python generate_semi_synthetic_v6.py --count_per_cert 45 --output_dir ./semi_synth_certs_v6
```

### Generation Highlights:
- **Open-Vocabulary University Names**: 50% curated real institutions + 50% procedurally synthesized combinations to prevent token memorization.
- **Background Texture Blending**: Real certificate scans used as backdrops to preserve authentic paper creases, guilloché borders, and seals.
- **Multi-Typography Rendering**: Mixed fonts across Gothic diplomas, formal Latin scripts, and clean sans-serif numerals.
- **Realistic Distortions**: Mild perspective skews ($\pm 2^\circ$), lighting vignettes, scanner noise, and DPI variations.

---

## 🚀 Model Training & Iterations (v2 → v6)

Fine-tuning is conducted on [naver-clova-ix/donut-base](https://huggingface.co/naver-clova-ix/donut-base) using PyTorch and Hugging Face Transformers.

### Evolution Across Iterations:
- **v2 Baseline**: Initial proof-of-concept; high character error on long degree titles; confused conferral dates with issue dates.
- **v4 Expansion**: Introduced open-vocabulary university generation and 20+ pass class variants (Honours, Distinction, Division).
- **v5 Optimization**: Upgraded date normalization logic and improved bounding box spatial heuristics.
- **v6 Current**: Blur-free augmentation pipeline, multi-line degree specialization parsing, robust date anchor supervision, and 95%+ field-level extraction accuracy.

---

## 💻 Web Application Setup

The project includes an interactive web interface featuring live drag-and-drop uploads, visual bounding-box highlights, side-by-side verification, and **one-click CSV / JSON export**.

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** & `npm`
- **Tesseract OCR** (Optional, required for bounding box overlays):
  - Windows: [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) (Add to PATH)
  - Ubuntu/Debian: `sudo apt install tesseract-ocr`

### 1. Backend Setup (FastAPI)

```bash
# Navigate to backend
cd degree-extract-webapp/backend

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server (serves on http://localhost:8000)
python -m uvicorn main_v6:app --reload --port 8000
```

### 2. Frontend Setup (React + Vite)

```bash
# In a new terminal, navigate to frontend
cd degree-extract-webapp/frontend

# Install dependencies
npm install

# Start Vite development server (serves on http://localhost:5173)
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 📡 API Reference

### `POST /extract`
Uploads a certificate image and returns structured predictions along with bounding boxes.

- **Request**: `multipart/form-data` with `file: <image_file>`
- **Response**:
```json
{
  "fields": {
    "candidate_name": "Shah Vrushti T.",
    "university": "Dharmsinh Desai University",
    "degree": "Bachelor of Technology",
    "specialization": "Information Technology",
    "pass_class": "First Class with Distinction",
    "issue_date": "16-10-2025",
    "authority_name": "Vice Chancellor"
  },
  "missing_fields": [],
  "boxes": {
    "candidate_name": [420, 510, 890, 560],
    "university": [250, 180, 1050, 260]
  },
  "annotated_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}
```

### `GET /health`
Returns backend health status, CUDA acceleration status, and active model version.

---

## 📊 Evaluation Results

| Field | v2 Precision | v4 Precision | v6 Precision (Current) |
| :--- | :---: | :---: | :---: |
| **Candidate Name** | 87.2% | 94.1% | **97.8%** |
| **University Name** | 82.5% | 91.8% | **96.4%** |
| **Degree Conferred** | 79.4% | 89.6% | **95.2%** |
| **Specialization** | 71.0% | 84.3% | **92.1%** |
| **Pass Class / Grade**| 68.5% | 88.0% | **94.7%** |
| **Issue / Passing Date**| 74.1% | 86.5% | **95.6%** |

---

## 📜 License & Citation

This project is released under the **MIT License**.

If you use or build upon this work, please cite:
```bibtex
@misc{shah2025degreedetailextract,
  author = {Shah, Vrushti T. and Prajapati, Harshadkumar B.},
  title = {Degree Certificate Detail Extraction using End-to-End Document Understanding Transformers},
  year = {2025},
  institution = {Dharmsinh Desai University, Department of Information Technology}
}
```
