#!/usr/bin/env python3
"""
PDF Hindi Extractor & 2-Up Stitcher - Web Application Backend
============================================================
Flask server providing REST APIs for:
  - Drag-and-drop / file queue upload
  - Interactive page preview with visual divider line detection
  - Single-file and batch 2-Up or Single-column processing
  - In-browser PDF preview and single / ZIP downloads
  - Processing statistics (pages saved, paper reduction)
"""

import base64
import io
import os
import sys
import uuid
import zipfile
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file
import pymupdf

# Ensure extract_hindi engine can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_hindi import extract_and_stitch, find_divider_line, get_page_preview

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 250 * 1024 * 1024  # 250 MB limit

# In-memory store for session metadata
files_db = {}
results_db = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload_files():
    """Upload one or more PDF files and return their metadata."""
    if "files" not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    uploaded = request.files.getlist("files")
    saved_files = []

    for f in uploaded:
        if not f.filename.lower().endswith(".pdf"):
            continue

        file_id = str(uuid.uuid4())[:8]
        safe_name = os.path.basename(f.filename)
        save_path = os.path.join(UPLOAD_DIR, f"{file_id}_{safe_name}")
        f.save(save_path)

        try:
            doc = pymupdf.open(save_path)
            page_count = len(doc)
            file_size_kb = round(os.path.getsize(save_path) / 1024, 1)
            doc.close()

            files_db[file_id] = {
                "file_id": file_id,
                "original_filename": safe_name,
                "path": save_path,
                "total_pages": page_count,
                "size_kb": file_size_kb,
                "uploaded_at": datetime.now().strftime("%H:%M:%S"),
            }
            saved_files.append(files_db[file_id])
        except Exception as e:
            return jsonify({"error": f"Failed to read PDF '{safe_name}': {str(e)}"}), 400

    return jsonify({"success": True, "files": saved_files})


@app.route("/api/preview/<file_id>/<int:page_idx>")
def page_preview(file_id, page_idx):
    """
    Generate page preview image with detected divider line.
    Supports query parameters:
      - dpi: render resolution (default 110)
      - offset: manual point shift (default 0.0)
    """
    file_info = files_db.get(file_id)
    if not file_info:
        return jsonify({"error": "File not found"}), 404

    dpi = int(request.args.get("dpi", 110))
    offset = float(request.args.get("offset", 0.0))

    try:
        preview_data = get_page_preview(file_info["path"], page_idx=page_idx, dpi=dpi, offset_pt=offset)
        b64_img = base64.b64encode(preview_data["image_bytes"]).decode("utf-8")

        return jsonify({
            "success": True,
            "page_idx": page_idx,
            "total_pages": preview_data["total_pages"],
            "width_pt": preview_data["width_pt"],
            "height_pt": preview_data["height_pt"],
            "divider_x_pt": preview_data["divider_x_pt"],
            "divider_x_pct": preview_data["divider_x_pct"],
            "image_data": f"data:image/png;base64,{b64_img}",
        })
    except Exception as e:
        return jsonify({"error": f"Preview failed: {str(e)}"}), 500


@app.route("/api/process", methods=["POST"])
def process_pdf():
    """
    Process PDF with options:
      - file_id
      - mode: "2up" or "single"
      - side: "left", "right", or "both"
      - skip_pages: list or comma-separated string
      - offset_pt: float
      - draw_line: bool
    """
    data = request.json or {}
    file_ids = data.get("file_ids", [])
    if isinstance(file_ids, str):
        file_ids = [file_ids]

    if not file_ids:
        return jsonify({"error": "No file_ids provided"}), 400

    mode = data.get("mode", "2up")
    merge_2up = (mode == "2up")
    side = data.get("side", "left")  # left, right, both
    offset_pt = float(data.get("offset_pt", 0.0))
    draw_line = bool(data.get("draw_line", True))

    # Parse skip_pages
    skip_raw = data.get("skip_pages", "")
    skip_set = set()
    if isinstance(skip_raw, list):
        skip_set = set(skip_raw)
    elif isinstance(skip_raw, str) and skip_raw.strip():
        for part in skip_raw.split(","):
            part = part.strip()
            if part.isdigit():
                skip_set.add(int(part))

    processed_results = []

    for fid in file_ids:
        finfo = files_db.get(fid)
        if not finfo:
            continue

        base_name, _ = os.path.splitext(finfo["original_filename"])
        sides_to_run = ["left", "right"] if side == "both" else [side]

        for s in sides_to_run:
            result_id = str(uuid.uuid4())[:8]
            suffix = "_hindi" if s == "left" else "_english"
            mode_tag = "_2up" if merge_2up else "_single"
            out_filename = f"{base_name}{suffix}{mode_tag}.pdf"
            out_path = os.path.join(OUTPUT_DIR, f"{result_id}_{out_filename}")

            try:
                out_pages = extract_and_stitch(
                    finfo["path"],
                    out_path,
                    side=s,
                    skip_pages=skip_set,
                    merge_2up=merge_2up,
                    offset_pt=offset_pt,
                    draw_line=draw_line,
                )

                orig_pages = finfo["total_pages"] - len(skip_set)
                saved_sheets = max(0, orig_pages - out_pages) if merge_2up else 0
                savings_pct = round((saved_sheets / orig_pages) * 100, 1) if (merge_2up and orig_pages > 0) else 0

                res_info = {
                    "result_id": result_id,
                    "file_id": fid,
                    "original_filename": finfo["original_filename"],
                    "output_filename": out_filename,
                    "path": out_path,
                    "side": "Hindi" if s == "left" else "English",
                    "mode": "2-Up Booklet" if merge_2up else "Single-Column",
                    "original_pages": orig_pages,
                    "output_pages": out_pages,
                    "saved_sheets": saved_sheets,
                    "savings_pct": savings_pct,
                    "file_size_kb": round(os.path.getsize(out_path) / 1024, 1),
                    "created_at": datetime.now().strftime("%H:%M:%S"),
                }
                results_db[result_id] = res_info
                processed_results.append(res_info)

            except Exception as e:
                return jsonify({"error": f"Failed processing '{finfo['original_filename']}': {str(e)}"}), 500

    return jsonify({"success": True, "results": processed_results})


@app.route("/api/download/<result_id>")
def download_result(result_id):
    """Download the processed PDF file."""
    res = results_db.get(result_id)
    if not res or not os.path.isfile(res["path"]):
        return jsonify({"error": "File not found"}), 404

    return send_file(
        res["path"],
        as_attachment=True,
        download_name=res["output_filename"],
        mimetype="application/pdf",
    )


@app.route("/api/preview-pdf/<result_id>")
def preview_pdf(result_id):
    """Stream PDF directly for in-browser iframe viewing."""
    res = results_db.get(result_id)
    if not res or not os.path.isfile(res["path"]):
        return jsonify({"error": "File not found"}), 404

    return send_file(
        res["path"],
        as_attachment=False,
        mimetype="application/pdf",
    )


@app.route("/api/batch-download", methods=["POST"])
def batch_download():
    """Create a ZIP file of multiple processed PDFs."""
    data = request.json or {}
    result_ids = data.get("result_ids", [])
    if not result_ids:
        return jsonify({"error": "No result_ids provided"}), 400

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for rid in result_ids:
            res = results_db.get(rid)
            if res and os.path.isfile(res["path"]):
                zip_file.write(res["path"], arcname=res["output_filename"])

    zip_buffer.seek(0)
    zip_name = f"processed_hindi_exams_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=zip_name,
        mimetype="application/zip",
    )


@app.route("/api/history")
def get_history():
    """Return all processed files in this session."""
    return jsonify({"history": list(results_db.values())})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n=========================================================")
    print(f" PDF Hindi Extractor & 2-Up Stitcher GUI")
    print(f" Web GUI running at: http://127.0.0.1:{port}")
    print(f" Press Ctrl+C to stop server")
    print(f"=========================================================\n")
    app.run(host="127.0.0.1", port=port, debug=False)
