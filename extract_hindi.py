#!/usr/bin/env python3
"""
PDF Hindi Question Extractor & 2-Up Stitcher
============================================
Extracts the Hindi (left) or English (right) half from bilingual exam PDFs
using slice-based physical divider line detection, and merges consecutive
pages side-by-side (1+2, 3+4, ...) to save 50% paper and create a standard A4 booklet.

Usage:
    python extract_hindi.py "exam.pdf"                     # 2-up merged Hindi booklet (default)
    python extract_hindi.py "exam.pdf" --single-column     # Separate half-width pages
    python extract_hindi.py "exam.pdf" --side right        # Extract English column instead
    python extract_hindi.py "exam.pdf" --skip-pages 0      # Skip page 0 (if it's a cover)
    python extract_hindi.py "exam.pdf" -o "output.pdf"     # Custom output file

Dependencies: pymupdf, Pillow, numpy
"""

import argparse
import io
import os
import sys

import numpy as np
import pymupdf
from PIL import Image


def find_divider_line(page, dpi=120):
    """
    Find the vertical dividing line between columns on a page.
    
    Renders the page at given DPI and analyzes horizontal slices across
    the content height (excluding header and footer). For each slice,
    it identifies the sharp dark peak in the central region (44% to 56% width).
    The median of peak locations gives the exact line coordinate, making it
    completely immune to scan rotation/tilt, broken line segments, and internal
    whitespace between question options.

    Returns:
        float: x-coordinate of the dividing line in PDF points.
    """
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    arr = np.array(img)
    scale = page.rect.width / arr.shape[1]

    h, w = arr.shape
    # Content rows: 8% to 92% to avoid top/bottom border boxes and footer
    content = arr[int(h * 0.08):int(h * 0.92), :]
    ch, _ = content.shape

    min_x = int(w * 0.44)
    max_x = int(w * 0.56)

    n_slices = 10
    slice_h = ch // n_slices
    slice_peaks = []

    for s in range(n_slices):
        sl = content[s * slice_h:(s + 1) * slice_h, min_x:max_x]
        dark = (sl < 130).mean(axis=0)
        # Smooth with a small 3-pixel kernel to filter single-pixel noise
        dark_smooth = np.convolve(dark, [0.25, 0.5, 0.25], mode="same")
        peak_idx = np.argmax(dark_smooth)
        if dark_smooth[peak_idx] > 0.12:
            slice_peaks.append(min_x + peak_idx)

    if len(slice_peaks) >= 3:
        return np.median(slice_peaks) * scale

    # Fallback to exact midpoint if no distinct line was detected
    return page.rect.width / 2.0


def extract_and_stitch(input_pdf, output_pdf, side="left", skip_pages=None,
                       merge_2up=True, dpi=120, offset_pt=0.0, draw_line=True,
                       progress_callback=None):
    """
    Extracts column from input PDF and optionally stitches consecutive pairs 2-up.
    
    Args:
        input_pdf: path or BytesIO of source PDF
        output_pdf: path or BytesIO of destination PDF
        side: "left" for Hindi, "right" for English
        skip_pages: set of 0-indexed page numbers to skip
        merge_2up: whether to merge consecutive pages 2-up side-by-side
        dpi: render resolution for divider line detection
        offset_pt: manual shift in PDF points for the cut line (default 0.0)
        draw_line: whether to draw a vertical divider line between 2-up pages
        progress_callback: optional callable(current_step, total_steps)
    """
    skip_pages = skip_pages or set()
    doc = pymupdf.open(input_pdf) if isinstance(input_pdf, str) else pymupdf.open(stream=input_pdf, filetype="pdf")
    out_doc = pymupdf.open()

    # Collect valid page indices to process
    valid_pages = [i for i in range(len(doc)) if i not in skip_pages]
    total_valid = len(valid_pages)

    if merge_2up:
        # Process pages in pairs: (0, 1), (2, 3), etc.
        pair_count = (total_valid + 1) // 2
        for pair_idx in range(pair_count):
            idx1 = valid_pages[pair_idx * 2]
            idx2 = valid_pages[pair_idx * 2 + 1] if (pair_idx * 2 + 1) < total_valid else None

            p1 = doc[idx1]
            target_w = p1.rect.width
            target_h = p1.rect.height
            mid_x = target_w / 2.0

            new_page = out_doc.new_page(width=target_w, height=target_h)

            # Left slot: First page in pair
            line_x1 = find_divider_line(p1, dpi=dpi) + offset_pt
            if side == "left":
                crop1 = pymupdf.Rect(p1.rect.x0, p1.rect.y0, line_x1 + 1.0, p1.rect.y1)
            else:
                crop1 = pymupdf.Rect(line_x1 - 1.0, p1.rect.y0, p1.rect.x1, p1.rect.y1)

            left_slot = pymupdf.Rect(0, 0, mid_x, target_h)
            new_page.show_pdf_page(left_slot, doc, idx1, clip=crop1)

            # Right slot: Second page in pair (if available)
            if idx2 is not None:
                p2 = doc[idx2]
                line_x2 = find_divider_line(p2, dpi=dpi) + offset_pt
                if side == "left":
                    crop2 = pymupdf.Rect(p2.rect.x0, p2.rect.y0, line_x2 + 1.0, p2.rect.y1)
                else:
                    crop2 = pymupdf.Rect(line_x2 - 1.0, p2.rect.y0, p2.rect.x1, p2.rect.y1)

                right_slot = pymupdf.Rect(mid_x, 0, target_w, target_h)
                new_page.show_pdf_page(right_slot, doc, idx2, clip=crop2)

            # Draw a subtle vertical separator between the two merged columns
            if draw_line:
                new_page.draw_line(
                    pymupdf.Point(mid_x, 35),
                    pymupdf.Point(mid_x, target_h - 35),
                    color=(0.25, 0.25, 0.25),
                    width=0.7,
                )

            if progress_callback:
                progress_callback(pair_idx + 1, pair_count)
            else:
                print(f"\r  Processing 2-up sheet: {pair_idx + 1}/{pair_count}", end="")
    else:
        # Output individual half-width pages
        for step, page_num in enumerate(valid_pages):
            page = doc[page_num]
            line_x = find_divider_line(page, dpi=dpi) + offset_pt

            if side == "left":
                crop = pymupdf.Rect(page.rect.x0, page.rect.y0, line_x + 1.0, page.rect.y1)
            else:
                crop = pymupdf.Rect(line_x - 1.0, page.rect.y0, page.rect.x1, page.rect.y1)

            new_page = out_doc.new_page(width=crop.width, height=crop.height)
            new_page.show_pdf_page(new_page.rect, doc, page_num, clip=crop)

            if progress_callback:
                progress_callback(step + 1, total_valid)
            else:
                print(f"\r  Processing page: {step + 1}/{total_valid}", end="")

    print()
    total_pages = len(out_doc)
    if isinstance(output_pdf, str):
        out_doc.save(output_pdf)
    else:
        out_doc.save(output_pdf)
    out_doc.close()
    doc.close()

    return total_pages


def get_page_preview(doc_or_path, page_idx=0, dpi=100, offset_pt=0.0):
    """
    Generate page preview image as PNG bytes along with detected divider line.
    
    Returns:
        dict: {
            "image_bytes": bytes,
            "width_pt": float,
            "height_pt": float,
            "divider_x_pt": float,
            "divider_x_pct": float
        }
    """
    doc = pymupdf.open(doc_or_path) if isinstance(doc_or_path, str) else doc_or_path
    page = doc[page_idx]
    divider_x = find_divider_line(page, dpi=dpi) + offset_pt
    divider_pct = (divider_x / page.rect.width) * 100.0

    pix = page.get_pixmap(dpi=dpi)
    img_bytes = pix.tobytes("png")

    return {
        "image_bytes": img_bytes,
        "width_pt": page.rect.width,
        "height_pt": page.rect.height,
        "divider_x_pt": round(divider_x, 2),
        "divider_x_pct": round(divider_pct, 2),
        "total_pages": len(doc)
    }


def generate_output_path(input_path, side):
    """Generate default output path next to input file."""
    base, ext = os.path.splitext(input_path)
    suffix = "_hindi" if side == "left" else "_english"
    return f"{base}{suffix}{ext}"


def main():
    parser = argparse.ArgumentParser(
        description="Extract Hindi (left) or English (right) half from bilingual exam PDFs with optional 2-up stitching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "exam.pdf"                     Extract Hindi & stitch 2-up (1+2, 3+4 ...)
  %(prog)s "exam.pdf" --single-column     Extract Hindi as half-width individual pages
  %(prog)s "exam.pdf" --side right        Extract English column instead
  %(prog)s "exam.pdf" --skip-pages 0      Skip page 0 (instructions/cover page)
  %(prog)s "exam.pdf" -o "out.pdf"        Specify custom output filename
        """,
    )
    parser.add_argument("input", help="Path to the input bilingual exam PDF")
    parser.add_argument("-o", "--output", help="Output PDF path (default: <input>_hindi.pdf)")
    parser.add_argument(
        "--side",
        choices=["left", "right"],
        default="left",
        help="Which half to extract: left=Hindi, right=English (default: left)",
    )
    parser.add_argument(
        "--skip-pages",
        default="",
        help="Comma-separated 0-indexed page numbers to skip (default: none)",
    )
    parser.add_argument(
        "--single-column",
        action="store_true",
        help="Output single half-width pages instead of 2-up merged standard A4 sheets",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=120,
        help="DPI for divider line detection (default: 120)",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"[ERROR] File not found: {args.input}")
        sys.exit(1)

    skip_pages = set()
    if args.skip_pages.strip():
        try:
            skip_pages = {int(p.strip()) for p in args.skip_pages.split(",") if p.strip()}
        except ValueError:
            print("[ERROR] --skip-pages must be comma-separated integers (e.g. '0,1')")
            sys.exit(1)

    output_path = args.output or generate_output_path(args.input, args.side)
    merge_2up = not args.single_column

    side_label = "Hindi (left)" if args.side == "left" else "English (right)"
    mode_label = "2-Up Merged (Side-by-Side: 1+2, 3+4...)" if merge_2up else "Single-Column Half Width"

    print(f"[INPUT]   {args.input}")
    print(f"[OUTPUT]  {output_path}")
    print(f"[SIDE]    {side_label}")
    print(f"[LAYOUT]  {mode_label}")
    if skip_pages:
        print(f"[SKIP]    pages {sorted(skip_pages)}")
    print()

    total_out = extract_and_stitch(
        args.input,
        output_path,
        side=args.side,
        skip_pages=skip_pages,
        merge_2up=merge_2up,
        dpi=args.dpi,
    )

    print(f"\n[DONE] {total_out} pages saved -> {output_path}")


if __name__ == "__main__":
    main()
