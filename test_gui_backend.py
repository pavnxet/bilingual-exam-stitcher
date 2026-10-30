#!/usr/bin/env python3
"""
Test script for Flask backend endpoints of PDF Hindi Extractor GUI.
Generates an in-memory sample bilingual PDF for testing with zero hardcoded paths.
"""

import io
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app
import pymupdf

def create_synthetic_exam_pdf():
    """Create a minimal 2-page bilingual exam PDF in memory."""
    doc = pymupdf.open()
    for page_num in range(2):
        page = doc.new_page(width=595.0, height=842.0)
        # Left column (Hindi placeholder)
        page.draw_rect(pymupdf.Rect(40, 100, 260, 700), color=(0.8, 0.8, 0.8), fill=(0.95, 0.95, 0.95))
        # Center vertical divider line at x = 297.5 pt
        page.draw_line(pymupdf.Point(297.5, 50), pymupdf.Point(297.5, 790), color=(0, 0, 0), width=1.5)
        # Right column (English placeholder)
        page.draw_rect(pymupdf.Rect(330, 100, 550, 700), color=(0.8, 0.8, 0.8), fill=(0.95, 0.95, 0.95))
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return buf.getvalue()

def run_tests():
    print("Testing Flask Web GUI endpoints...")
    client = app.test_client()

    # 1. Test Home page
    res = client.get("/")
    assert res.status_code == 200, f"GET / failed: {res.status_code}"
    print("  [OK] GET / returned 200 and rendered HTML")

    # 2. Test File Upload with synthetic in-memory PDF
    pdf_bytes = create_synthetic_exam_pdf()
    data = {
        "files": (io.BytesIO(pdf_bytes), "mock_bilingual_exam.pdf")
    }
    res = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200, f"Upload failed: {res.status_code}"
    upload_json = res.get_json()
    assert upload_json.get("success"), "Upload success flag false"
    file_id = upload_json["files"][0]["file_id"]
    total_pages = upload_json["files"][0]["total_pages"]
    print(f"  [OK] POST /api/upload success: file_id={file_id}, pages={total_pages}")

    # 3. Test Preview endpoint
    res = client.get(f"/api/preview/{file_id}/0?offset=0.0&dpi=72")
    assert res.status_code == 200, f"Preview failed: {res.status_code}"
    prev_json = res.get_json()
    assert prev_json.get("success"), "Preview success flag false"
    divider_x = prev_json["divider_x_pt"]
    divider_pct = prev_json["divider_x_pct"]
    print(f"  [OK] GET /api/preview success: divider={divider_x}pt ({divider_pct}%)")

    # 4. Test Process endpoint (2-Up Mode)
    proc_payload = {
        "file_ids": [file_id],
        "mode": "2up",
        "side": "left",
        "skip_pages": [],
        "offset_pt": 0.0,
        "draw_line": True
    }
    res = client.post("/api/process", json=proc_payload)
    assert res.status_code == 200, f"Process failed: {res.status_code}"
    proc_json = res.get_json()
    assert proc_json.get("success"), "Process success flag false"
    result = proc_json["results"][0]
    result_id = result["result_id"]
    out_pages = result["output_pages"]
    saved_sheets = result["saved_sheets"]
    print(f"  [OK] POST /api/process success: 2-up output={out_pages} pages, saved={saved_sheets} sheets")

    # 5. Test Download endpoint
    res = client.get(f"/api/download/{result_id}")
    assert res.status_code == 200, f"Download failed: {res.status_code}"
    assert res.mimetype == "application/pdf", f"Unexpected mimetype: {res.mimetype}"
    print(f"  [OK] GET /api/download success: size={len(res.data)} bytes")

    # 6. Test Batch Download (ZIP)
    res = client.post("/api/batch-download", json={"result_ids": [result_id]})
    assert res.status_code == 200, f"Batch download failed: {res.status_code}"
    assert res.mimetype == "application/zip", f"Unexpected zip mimetype: {res.mimetype}"
    print(f"  [OK] POST /api/batch-download success: zip size={len(res.data)} bytes")

    # 7. Test History endpoint
    res = client.get("/api/history")
    assert res.status_code == 200, f"History failed: {res.status_code}"
    hist_json = res.get_json()
    assert len(hist_json.get("history", [])) >= 1, "History empty"
    print(f"  [OK] GET /api/history success: {len(hist_json['history'])} records")

    print("\nALL FLASK BACKEND TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
