# Bilingual Exam PDF Splitter & 2-Up Booklet Stitcher

[![GitHub Pages](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-brightgreen?style=flat&logo=github)](https://pavnxet.github.io/bilingual-exam-stitcher/)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![100% In-Browser](https://img.shields.io/badge/Privacy-100%25%20Client--Side-green.svg)](#privacy--security)

An intelligent tool designed to extract single-language questions (e.g. Hindi or English) from bilingual two-column exam papers, and stitch consecutive pages **2-up side-by-side** onto standard A4 sheets. 

**Reduces total paper and printed pages by 50% while producing clean, professional question booklets.**

---

## 🌐 Try It Live in Your Browser (No Installation)

👉 **[https://pavnxet.github.io/bilingual-exam-stitcher/](https://pavnxet.github.io/bilingual-exam-stitcher/)**

*Runs 100% client-side in your browser via `pdf.js` and `pdf-lib`. Your files are never uploaded to any server.*

---

## 🎯 The Problem

Bilingual competitive exam papers (such as teacher recruitment tests, civil service exams, and board papers) typically format questions across two vertical columns:
- **Left Column**: Hindi
- **Right Column**: English

When preparing or printing these papers for single-medium study:
1. **Half the page is wasted**: Printing both languages requires double the paper and toner.
2. **Naive cuts fail**: Scanned test booklets are often slightly tilted (~0.5°), and whitespace between question option columns (e.g., `(1) ...` and `(2) ...`) causes standard whitespace detectors to erroneously slice right through questions.
3. **Uneven margins**: The central dividing line often shifts across pages by 90+ points.

---

## 💡 The Solution

This tool uses a **10-Slice Physical Divider Detection Algorithm**:
1. It partitions each page height into 10 horizontal slices.
2. It detects the sharp dark peak of the printed center divider line in each slice.
3. It takes the median peak location, making it **100% immune to scanner tilt, broken lines, or internal whitespace gaps between options**.
4. It extracts the desired language column (e.g., Hindi) and stitches consecutive pages (1+2, 3+4...) side-by-side onto standard A4 pages with a subtle dividing line.

```
Original Bilingual PDF (30 Pages)           2-Up Merged Booklet (15 Pages)
┌──────────────┬──────────────┐             ┌──────────────┬──────────────┐
│ Page 1 Hindi │ Page 1 Eng   │             │ Page 1 Hindi │ Page 2 Hindi │
├──────────────┼──────────────┤    ───►     ├──────────────┼──────────────┤
│ Page 2 Hindi │ Page 2 Eng   │             │ Page 3 Hindi │ Page 4 Hindi │
└──────────────┴──────────────┘             └──────────────┴──────────────┘
```

---

## ✨ Key Features

- **2-Up Booklet Stitching (Default)**: Merges consecutive odd + even pages (1+2, 3+4...) onto standard A4 sheets to cut printed pages in half.
- **Single-Column Mode**: Option to export individual half-width pages for mobile reading or digital cards.
- **Robust Divider Lock**: 10-slice peak detection algorithm tested across dozens of scanned exam papers with zero text clipping.
- **Language Switcher**: Extract Hindi (left), English (right), or Dual Mode (creates two separate booklets simultaneously).
- **Page Filtering**: One-click "Skip Cover Page" (instructions page) and custom page range skipping.
- **Interactive Cut Line Visualizer**: Live canvas inspector showing the page with an overlaid cut line and interactive offset slider (`-30pt` to `+30pt`).
- **Drag & Drop Multi-File Queue**: Batch process multiple exam papers in a single click with ZIP archive download.
- **In-Browser PDF Viewer**: Review generated booklets directly inside the browser before downloading.
- **Zero-Dependency Static App**: The web app runs completely client-side on GitHub Pages.

---

## 🚀 Quick Start

### Mode 1: Online on GitHub Pages (Recommended)
Open **[https://pavnxet.github.io/bilingual-exam-stitcher/](https://pavnxet.github.io/bilingual-exam-stitcher/)**, drag-and-drop your PDF, and click **Start Processing**.

---

### Mode 2: Local Web GUI (Windows One-Click)
1. Clone this repository:
   ```bash
   git clone https://github.com/pavnxet/bilingual-exam-stitcher.git
   cd bilingual-exam-stitcher
   ```
2. Double-click `run_gui.bat` (or run `python app.py`).
3. Your browser will automatically open to `http://127.0.0.1:5000`.

---

### Mode 3: Python CLI
Install dependencies:
```bash
pip install -r requirements.txt
```

Run extraction on any exam PDF:
```bash
# Standard 2-Up merge (Hindi left + next page Hindi right)
python extract_hindi.py "path/to/exam.pdf"

# If the PDF has an instructions cover page on page 0 that you want to skip:
python extract_hindi.py "path/to/exam.pdf" --skip-pages 0

# Extract English questions instead:
python extract_hindi.py "path/to/exam.pdf" --side right

# Export single half-width pages instead of 2-up merging:
python extract_hindi.py "path/to/exam.pdf" --single-column

# Specify custom output filename:
python extract_hindi.py "path/to/exam.pdf" -o "compact_hindi.pdf"
```

---

## ⚙️ CLI Reference

| Flag | Default | Description |
|---|---|---|
| `input` | *(Required)* | Path to the source bilingual PDF. |
| `-o`, `--output` | `<input>_hindi.pdf` | Destination PDF path. |
| `--side` | `left` | Which column to extract (`left` for Hindi, `right` for English). |
| `--skip-pages` | `""` | Comma-separated 0-indexed page numbers to skip (e.g. `0` for cover). |
| `--single-column` | `False` | Output individual half-width pages instead of 2-up A4 sheets. |
| `--dpi` | `120` | Resolution for divider line detection. |

---

## 🔒 Privacy & Security

When using the GitHub Pages web application:
- All PDF parsing, image rendering, divider detection, and stitching are executed **locally within your web browser's JavaScript sandbox**.
- No file is ever transmitted over the network or saved on any remote server.

---

## 📜 License

MIT License. Feel free to use, modify, and distribute for study or commercial use.
